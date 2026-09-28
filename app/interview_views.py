import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import InterviewSession, InterviewQuestion, InterviewAnswer, InterviewFeedback
from .services.interview_service import InterviewService
from .services.speech_service import SpeechService
from .services.assemblyai_service import AssemblyAIService
import math
import os
from django.conf import settings

@login_required
def interview_setup_view(request):
    if request.method == "POST":
        interview_type = request.POST.get("interview_type")
        domain = request.POST.get("domain")
        technology = request.POST.get("technology", "General")
        if not technology:
            technology = "General"
        difficulty = request.POST.get("difficulty", "Intermediate")
        num_questions = int(request.POST.get("num_questions", 5))
        language = request.POST.get("interview_language", "English")

        service = InterviewService()
        session = service.create_session(
            user=request.user,
            interview_type=interview_type,
            domain=domain,
            technology=technology,
            difficulty=difficulty,
            num_questions=num_questions,
            language=language
        )
        
        first_question = session.questions.order_by('question_number').first()
        if first_question:
            return redirect('interview_question', session_id=session.id, question_id=first_question.id)
        else:
            return redirect('interview_report', session_id=session.id)

    return render(request, "interview_setup.html")

@login_required
def interview_question_view(request, session_id, question_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    question = get_object_or_404(InterviewQuestion, id=question_id, session=session)
    
    # Check if answer already exists
    if hasattr(question, 'answer'):
        return redirect('interview_feedback', session_id=session.id, question_id=question.id)

    if request.method == "POST":
        transcript = request.POST.get("transcript", "")
        duration_seconds = int(request.POST.get("duration", 0))
        audio_file = request.FILES.get("audio_file")

        # Basic STT or handle file
        speech_service = SpeechService()
        audio_path = ""
        if audio_file:
            audio_path = speech_service.save_audio_file(audio_file, request.user.id)
            try:
                aai_service = AssemblyAIService()
                if aai_service.is_enabled():
                    full_audio_path = os.path.join(settings.BASE_DIR, audio_path)
                    aai_result = aai_service.transcribe_audio(full_audio_path)
                    if aai_result.get("status") == "completed" and aai_result.get("text"):
                        transcript = aai_result.get("text", transcript)
            except Exception:
                pass
        
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
            audio_file=audio_path,
            word_count=word_count,
            filler_count=filler_count,
            speaking_rate=speaking_rate,
            answer_status=answer_status
        )
        
        visual_metrics_raw = request.POST.get("visual_metrics")
        if visual_metrics_raw:
            try:
                vm_data = json.loads(visual_metrics_raw)
                from app.models import VisualPresence
                VisualPresence.objects.create(
                    interview_answer=answer,
                    eye_contact_pct=vm_data.get("eye_contact_pct", 0),
                    expression_variety_score=vm_data.get("expression_variety_score", 0),
                    posture_score=vm_data.get("posture_score", 0),
                    face_detected_pct=vm_data.get("face_detected_pct", 0),
                    gesture_activity_score=vm_data.get("gesture_activity_score")
                )
            except Exception as e:
                print("Error saving visual metrics:", e)

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
        eval_data = service.evaluate_answer(answer, session.interview_language)
        
        evaluation_status = eval_data.get("evaluation_status", "EVALUATED")

        # Scoring based on weights:
        pace_score = 100 if 100 <= speaking_rate <= 160 else max(0, 100 - abs(speaking_rate - 130))
        filler_score = max(0, 100 - (filler_count * 10))

        if evaluation_status == "FAILED":
            # Save feedback but do not manufacture a score
            InterviewFeedback.objects.create(
                answer=answer,
                evaluation_status="FAILED",
                classification="Not Evaluated",
                feedback_text="AI evaluation is temporarily unavailable."
            )
            # We don't overwrite answer.score so it stays 0, but it won't be shown
        else:
            ai_overall = eval_data.get("overall_score", 0)
            final_score = (ai_overall * 0.90) + (pace_score * 0.05) + (filler_score * 0.05)
            answer.score = round(final_score, 2)
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
                missing_points_json=json.dumps(eval_data.get("missing_points", [])),
                correct_points_json=json.dumps(eval_data.get("correct_points", [])),
                incorrect_points_json=json.dumps(eval_data.get("incorrect_points", [])),
                suggestions_json=json.dumps(eval_data.get("suggestions", []))
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
    feedback = answer.feedback
    
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
def interview_retry_feedback_view(request, session_id, question_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    question = get_object_or_404(InterviewQuestion, id=question_id, session=session)
    answer = get_object_or_404(InterviewAnswer, question=question)
    feedback = get_object_or_404(InterviewFeedback, answer=answer)

    # Only retry if evaluation actually failed and user actually answered
    if feedback.evaluation_status == "FAILED" and answer.answer_status == "ANSWERED":
        service = InterviewService()
        eval_data = service.evaluate_answer(answer, session.interview_language)
        
        evaluation_status = eval_data.get("evaluation_status", "EVALUATED")
        
        if evaluation_status != "FAILED":
            # Success, update everything
            ai_overall = eval_data.get("overall_score", 0)
            
            # Recalculate blended score
            pace_score = 100 if 100 <= answer.speaking_rate <= 160 else max(0, 100 - abs(answer.speaking_rate - 130))
            filler_score = max(0, 100 - (answer.filler_count * 10))
            
            final_score = (ai_overall * 0.90) + (pace_score * 0.05) + (filler_score * 0.05)
            answer.score = round(final_score, 2)
            answer.save()

            feedback.evaluation_status = "EVALUATED"
            feedback.classification = eval_data.get("classification", "Not Answered")
            feedback.relevance_score = eval_data.get("relevance", 0)
            feedback.technical_accuracy = eval_data.get("technical_correctness", 0)
            feedback.completeness_score = eval_data.get("completeness", 0)
            feedback.structure_score = eval_data.get("structure", 0)
            feedback.clarity_score = eval_data.get("clarity", 0)
            feedback.grammar_score = 0
            feedback.feedback_text = eval_data.get("feedback", "No feedback provided.")
            feedback.missing_points_json = json.dumps(eval_data.get("missing_points", []))
            feedback.correct_points_json = json.dumps(eval_data.get("correct_points", []))
            feedback.incorrect_points_json = json.dumps(eval_data.get("incorrect_points", []))
            feedback.suggestions_json = json.dumps(eval_data.get("suggestions", []))
            feedback.save()

    return redirect('interview_feedback', session_id=session.id, question_id=question.id)

@login_required
def interview_report_view(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    
    questions = session.questions.all().order_by('question_number')
    total_score = 0
    completed = 0
    for q in questions:
        if hasattr(q, 'answer'):
            total_score += q.answer.score
            completed += 1
            
    if completed > 0:
        session.final_score = round(total_score / completed, 2)
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
