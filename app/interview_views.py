import json
import math
import os
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from .models import InterviewSession, InterviewQuestion, InterviewAnswer, InterviewFeedback
from .services.interview_service import InterviewService
from .services.speech_service import SpeechService
from .services.assemblyai_service import AssemblyAIService
from .utils import safe_int, ratelimit_view, validate_audio_file, validate_and_clean_visual_metrics

@login_required
def interview_setup_view(request):
    if request.method == "POST":
        interview_type = request.POST.get("interview_type")
        domain = request.POST.get("domain")
        technology = request.POST.get("technology", "General")
        if not technology:
            technology = "General"
        difficulty = request.POST.get("difficulty", "Intermediate")
        raw_num = request.POST.get("num_questions")
        num_questions = safe_int(raw_num, default=None, min=1, max=15)
        if num_questions is None:
            messages.error(request, "Please choose a valid number of questions between 1 and 15.")
            return render(request, "interview_setup.html", status=400)
        language = request.POST.get("interview_language", "English")

        service = InterviewService()
        try:
            session = service.create_session(
                user=request.user,
                interview_type=interview_type,
                domain=domain,
                technology=technology,
                difficulty=difficulty,
                num_questions=num_questions,
                language=language
            )
        except Exception as e:
            from app.services.gemini_service import map_gemini_exception
            mapped = map_gemini_exception(e)
            messages.error(request, f"AI Interview Question Generation Unavailable: {mapped.message} (code: {mapped.code})")
            return render(request, "interview_setup.html", {
                "error_message": mapped.message,
                "error_code": mapped.code
            }, status=503)
        
        first_question = session.questions.order_by('question_number').first()
        if first_question:
            return redirect('interview_question', session_id=session.id, question_id=first_question.id)
        else:
            return redirect('interview_report', session_id=session.id)

    return render(request, "interview_setup.html")

@login_required
@ratelimit_view("10/m")
def interview_question_view(request, session_id, question_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    question = get_object_or_404(InterviewQuestion, id=question_id, session=session)
    
    # Check if answer already exists
    if hasattr(question, 'answer'):
        return redirect('interview_feedback', session_id=session.id, question_id=question.id)

    if request.method == "POST":
        transcript = request.POST.get("transcript", "")
        raw_duration = request.POST.get("duration", 0)
        duration_seconds = safe_int(raw_duration, default=0, min=0, clamp=True)
        audio_file = request.FILES.get("audio_file")

        if audio_file:
            is_valid_audio, audio_err = validate_audio_file(audio_file)
            if not is_valid_audio:
                messages.error(request, audio_err)
                return redirect('interview_question', session_id=session.id, question_id=question.id)

        service = InterviewService()
        word_count = len(transcript.split())
        filler_count = service.analyze_filler_words(transcript)
        speaking_rate = int((word_count / max(1, duration_seconds)) * 60) if duration_seconds > 0 else 0

        # 1. Answer Detection
        answer_status = "ANSWERED" if transcript.strip() else "NOT_ANSWERED"

        answer = InterviewAnswer.objects.create(
            question=question,
            transcript=transcript,
            duration_seconds=duration_seconds,
            word_count=word_count,
            filler_count=filler_count,
            speaking_rate=speaking_rate,
            answer_status=answer_status
        )

        if audio_file:
            ext = os.path.splitext(getattr(audio_file, "name", "interview.webm"))[1].lower() or ".webm"
            filename = f"interview_{uuid.uuid4().hex}{ext}"
            answer.audio_file.save(filename, audio_file, save=True)

            if not transcript or not transcript.strip():
                try:
                    aai_service = AssemblyAIService()
                    if aai_service.is_enabled():
                        aai_result = aai_service.transcribe_audio(answer.audio_file.path)
                        if aai_result.get("status") == "completed" and aai_result.get("text"):
                            answer.transcript = aai_result.get("text")
                            answer.word_count = len(answer.transcript.split())
                            answer.filler_count = service.analyze_filler_words(answer.transcript)
                            answer.speaking_rate = int((answer.word_count / max(1, duration_seconds)) * 60) if duration_seconds > 0 else 0
                            answer.answer_status = "ANSWERED"
                            answer.save()
                except Exception:
                    pass
        
        visual_metrics_raw = request.POST.get("visual_metrics")
        if visual_metrics_raw:
            try:
                vm_data = json.loads(visual_metrics_raw) if isinstance(visual_metrics_raw, str) else visual_metrics_raw
                cleaned_vm = validate_and_clean_visual_metrics(vm_data)
                if cleaned_vm:
                    from app.models import VisualPresence
                    VisualPresence.objects.create(
                        interview_answer=answer,
                        eye_contact_pct=cleaned_vm.get("eye_contact_pct", 0),
                        expression_variety_score=cleaned_vm.get("expression_variety_score", 0),
                        posture_score=cleaned_vm.get("posture_score", 0),
                        face_detected_pct=cleaned_vm.get("face_detected_pct", 0),
                        gesture_activity_score=cleaned_vm.get("gesture_activity_score")
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error saving visual metrics: {e}")

        if answer_status == "NOT_ANSWERED":
            # Don't evaluate, just record as not answered
            InterviewFeedback.objects.create(
                answer=answer,
                evaluation_status="EVALUATED",
                classification="Not Answered",
                feedback_text="No answer was provided."
            )
            answer.score = 0
            answer.save()
            session.completed_questions += 1
            session.save()
            return redirect('interview_feedback', session_id=session.id, question_id=question.id)

        # AI Evaluation
        from app.services.gemini_service import GeminiEvaluationError, map_gemini_exception
        from django.utils import timezone
        try:
            eval_data = service.evaluate_answer(answer, session.interview_language)
            evaluation_status = eval_data.get("evaluation_status", "EVALUATED")
            error_code = ""
            error_message = ""
        except GeminiEvaluationError as gee:
            eval_data = None
            evaluation_status = "FAILED"
            error_code = gee.code
            error_message = gee.message
        except Exception as exc:
            mapped = map_gemini_exception(exc, model_name=service.model_name)
            eval_data = None
            evaluation_status = "FAILED"
            error_code = mapped.code
            error_message = mapped.message

        if evaluation_status == "FAILED" or not eval_data:
            # Save feedback with error but do not manufacture a score
            InterviewFeedback.objects.create(
                answer=answer,
                evaluation_status="FAILED",
                error_code=error_code,
                error_message=error_message,
                classification="Not Evaluated",
                feedback_text=f"AI evaluation is temporarily unavailable: {error_message}"
            )
            answer.score = 0
            answer.save()
        else:
            ai_overall = eval_data.get("overall_score", 0)
            answer.score = round(ai_overall, 2)
            answer.save()

            InterviewFeedback.objects.create(
                answer=answer,
                evaluation_status="EVALUATED",
                classification=eval_data.get("classification", "Not Answered"),
                relevance_score=eval_data.get("relevance", 0),
                technical_accuracy=eval_data.get("technical_correctness", 0),
                completeness_score=eval_data.get("completeness", 0),
                structure_score=eval_data.get("structure", 0),
                clarity_score=eval_data.get("clarity", 0),
                grammar_score=0,
                feedback_text=eval_data.get("feedback", "No feedback provided."),
                model_answer=eval_data.get("model_answer", ""),
                missing_points_json=json.dumps(eval_data.get("missing_points", [])),
                correct_points_json=json.dumps(eval_data.get("correct_points", [])),
                incorrect_points_json=json.dumps(eval_data.get("incorrect_points", [])),
                suggestions_json=json.dumps(eval_data.get("suggestions", [])),
                engine=eval_data.get("engine", "gemini"),
                model_name=eval_data.get("model_name", service.model_name),
                raw_model_json=eval_data.get("raw_model_json", {}),
                evaluated_at=timezone.now(),
            )

        session.completed_questions += 1
        session.save()

        return redirect('interview_feedback', session_id=session.id, question_id=question.id)

    context = {
        "session": session,
        "question": question
    }
    return render(request, "interview_question.html", context)

@login_required
def interview_feedback_view(request, session_id, question_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    question = get_object_or_404(InterviewQuestion, id=question_id, session=session)
    answer = get_object_or_404(InterviewAnswer, question=question)
    feedback = getattr(answer, 'feedback', None)
    if not feedback:
        feedback, _ = InterviewFeedback.objects.get_or_create(
            answer=answer,
            defaults={
                "evaluation_status": "FAILED",
                "classification": "Pending",
                "feedback_text": "Evaluation feedback is being generated or was not completed. Click Retry to re-evaluate."
            }
        )
    
    # Determine next question
    next_question = session.questions.filter(question_number__gt=question.question_number).order_by('question_number').first()

    context = {
        "session": session,
        "question": question,
        "answer": answer,
        "feedback": feedback,
        "missing_points": json.loads(feedback.missing_points_json) if feedback.missing_points_json else [],
        "correct_points": json.loads(feedback.correct_points_json) if feedback.correct_points_json else [],
        "incorrect_points": json.loads(feedback.incorrect_points_json) if feedback.incorrect_points_json else [],
        "suggestions": json.loads(feedback.suggestions_json) if feedback.suggestions_json else [],
        "next_question": next_question
    }
    return render(request, "interview_feedback.html", context)

@login_required
@require_POST
def interview_retry_feedback_view(request, session_id, question_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    question = get_object_or_404(InterviewQuestion, id=question_id, session=session)
    answer = get_object_or_404(InterviewAnswer, question=question)
    feedback = get_object_or_404(InterviewFeedback, answer=answer)

    # Only retry if evaluation actually failed and user actually answered
    if feedback.evaluation_status == "FAILED" and answer.answer_status == "ANSWERED":
        service = InterviewService()
        from app.services.gemini_service import GeminiEvaluationError, map_gemini_exception
        from django.utils import timezone
        try:
            eval_data = service.evaluate_answer(answer, session.interview_language)
            ai_overall = eval_data.get("overall_score", 0)
            answer.score = round(ai_overall, 2)
            answer.save()

            feedback.evaluation_status = "EVALUATED"
            feedback.error_code = ""
            feedback.error_message = ""
            feedback.classification = eval_data.get("classification", "Not Answered")
            feedback.relevance_score = eval_data.get("relevance", 0)
            feedback.technical_accuracy = eval_data.get("technical_correctness", 0)
            feedback.completeness_score = eval_data.get("completeness", 0)
            feedback.structure_score = eval_data.get("structure", 0)
            feedback.clarity_score = eval_data.get("clarity", 0)
            feedback.grammar_score = 0
            feedback.feedback_text = eval_data.get("feedback", "No feedback provided.")
            feedback.model_answer = eval_data.get("model_answer", "")
            feedback.missing_points_json = json.dumps(eval_data.get("missing_points", []))
            feedback.correct_points_json = json.dumps(eval_data.get("correct_points", []))
            feedback.incorrect_points_json = json.dumps(eval_data.get("incorrect_points", []))
            feedback.suggestions_json = json.dumps(eval_data.get("suggestions", []))
            feedback.engine = eval_data.get("engine", "gemini")
            feedback.model_name = eval_data.get("model_name", service.model_name)
            feedback.raw_model_json = eval_data.get("raw_model_json", {})
            feedback.evaluated_at = timezone.now()
            feedback.save()
        except GeminiEvaluationError as gee:
            feedback.error_code = gee.code
            feedback.error_message = gee.message
            feedback.feedback_text = f"AI evaluation failed: {gee.message}"
            feedback.save()
        except Exception as exc:
            mapped = map_gemini_exception(exc, model_name=service.model_name)
            feedback.error_code = mapped.code
            feedback.error_message = mapped.message
            feedback.feedback_text = f"AI evaluation failed: {mapped.message}"
            feedback.save()

    return redirect('interview_feedback', session_id=session.id, question_id=question.id)

@login_required
def interview_report_view(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    
    questions = session.questions.all().order_by('question_number')
    answered_qs = [q for q in questions if hasattr(q, 'answer') and q.answer.answer_status == 'ANSWERED' and getattr(q.answer, 'feedback', None) and q.answer.feedback.evaluation_status == 'EVALUATED']
    if answered_qs:
        session.final_score = round(sum(q.answer.score for q in answered_qs) / len(answered_qs), 1)
    else:
        session.final_score = 0.0
    session.save()
        
    context = {
        "session": session,
        "questions": questions,
        "score_percentage": session.final_score
    }
    return render(request, "interview_report.html", context)

@login_required
def interview_history_view(request):
    sessions = InterviewSession.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "interview_history.html", {"sessions": sessions})

@login_required
def interview_performance_view(request):
    sessions = InterviewSession.objects.filter(user=request.user, completed_questions__gt=0).order_by('-created_at')
    
    # Aggregate data for skill gap analysis
    domains = {}
    for session in sessions:
        if session.domain not in domains:
            domains[session.domain] = []
        domains[session.domain].append(session.final_score)
        
    domain_averages = {d: round(sum(scores)/len(scores), 2) for d, scores in domains.items()}
    
    context = {
        "sessions": sessions,
        "domain_averages": domain_averages
    }
    return render(request, "interview_performance.html", context)
