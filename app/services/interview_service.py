import json
from django.conf import settings
from app.models import InterviewSession, InterviewQuestion, InterviewAnswer, InterviewFeedback
import os
import re

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

class InterviewService:
    def __init__(self):
        import logging
        import os
        from django.conf import settings
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            log_path = os.path.join(settings.BASE_DIR, 'logs', 'ai_evaluation.log')
            fh = logging.FileHandler(log_path)
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

        self.api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        self.logger.info("=========================================")
        self.logger.info(f"InterviewService initialized. API Key present: {bool(self.api_key)}")
        self.logger.info(f"GENAI_AVAILABLE: {GENAI_AVAILABLE}")
        
        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                self.model_name = 'gemini-3.8-flash'
                self.logger.info("Client successfully initialized!")
            except Exception as e:
                self.logger.error("Exception initializing client", exc_info=True)
                self.client = None
                self.model_name = None
        else:
            self.client = None
            self.model_name = None
            if not GENAI_AVAILABLE:
                self.logger.warning("GENAI_AVAILABLE is False. google-genai package is not installed.")

    def create_session(self, user, interview_type, domain, technology, difficulty, num_questions, language):
        session = InterviewSession.objects.create(
            user=user,
            interview_type=interview_type,
            domain=domain,
            technology=technology,
            difficulty=difficulty,
            total_questions=num_questions,
            interview_language=language
        )

        questions = self._generate_questions(interview_type, domain, technology, difficulty, num_questions, language)
        
        for i, q_data in enumerate(questions):
            InterviewQuestion.objects.create(
                session=session,
                question_text=q_data.get("question", "Could you discuss a core concept in this topic?"),
                question_number=i + 1,
                question_type=q_data.get("question_type", "General"),
                expected_points_json=json.dumps(q_data.get("expected_points", [])),
                ideal_answer=q_data.get("ideal_answer", ""),
                evaluation_criteria_json=json.dumps(q_data.get("evaluation_criteria", []))
            )
        return session

    def _generate_questions(self, interview_type, domain, technology, difficulty, num_questions, language):
        prompt = f"""
        You are an expert, senior-level interviewer in the "{domain}" domain.
        Your task is to generate exactly {num_questions} highly specific, realistic {difficulty} level questions for a "{interview_type}" interview.
        The questions MUST be deeply tailored to the topic/technology: "{technology}".

        Guidelines:
        - Technical Interview: Focus heavily on problem-solving, architectural choices, debugging, deep conceptual understanding, and practical scenarios.
        - HR Interview: Focus on introduction, strengths, weaknesses, career goals, teamwork, communication. DO NOT ask technical questions.
        - Behavioral Interview: Use situation-based (STAR) questions. (e.g. "Tell me about a time...")
        - Project Interview: Focus on objective, architecture, challenges, contributions, testing.
        - Coding Interview: Focus on algorithms, data structures, complexity.
        - Mixed: Provide a balanced mix.

        Every question must be unique. No generic placeholders. No introductory fluff.
        Ensure it matches {interview_type} and {technology} specifically.

        Return the result strictly as a JSON array of objects. Format:
        [
            {{
                "question": "The actual interview question string",
                "interview_type": "{interview_type}",
                "domain": "{domain}",
                "topic": "{technology}",
                "difficulty": "{difficulty}",
                "question_type": "Conceptual/Practical/Behavioral/etc",
                "expected_points": ["Point 1", "Point 2", "Point 3"],
                "ideal_answer": "A perfect, concise model answer.",
                "evaluation_criteria": ["Criteria 1", "Criteria 2", "Criteria 3"]
            }}
        ]
        """
        
        # Categorized fallback bank
        fallback_bank = {
            "HTML": {
                "Beginner": [
                    "What is HTML?",
                    "What is an HTML element?",
                    "What is the purpose of the <head> element?",
                    "What is the purpose of the <body> element?",
                    "How do you create a hyperlink in HTML?"
                ],
                "Intermediate": [
                    "Explain semantic HTML.",
                    "Explain HTML forms and validation.",
                    "Explain the difference between GET and POST.",
                    "Explain data-* attributes.",
                    "Explain script loading with async and defer.",
                    "Explain accessibility-related HTML practices."
                ],
                "Advanced": [
                    "Explain complex form accessibility considerations.",
                    "Explain how HTML parsing affects script execution.",
                    "Explain advanced semantic structure for large web applications.",
                    "Explain accessibility implications of dynamically generated HTML.",
                    "How do you implement Subresource Integrity (SRI)?"
                ]
            }
        }

        # Fallback question generation logic
        fallback_questions = []
        topic_bank = fallback_bank.get(technology, {}).get(difficulty, [
            f"Explain a core concept in {technology}.",
            f"What are the best practices in {technology}?",
            f"How do you handle errors in {technology}?",
            f"Explain a real-world use case for {technology}.",
            f"What are the common pitfalls in {technology}?"
        ])
        
        for i in range(num_questions):
            q_text = topic_bank[i % len(topic_bank)]
            if i >= len(topic_bank):
                q_text = f"{q_text} (Context {i+1})"
            
            fallback_questions.append({
                "question": q_text,
                "interview_type": interview_type,
                "domain": domain,
                "topic": technology,
                "difficulty": difficulty,
                "question_type": "Fallback",
                "expected_points": ["Relevant definition", "Practical example", "Best practices"],
                "ideal_answer": "A comprehensive and accurate explanation based on the topic.",
                "evaluation_criteria": ["Clarity", "Accuracy", "Relevance"]
            })

        if not self.client:
            return fallback_questions

        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                text = response.text.strip()
                
                # Robust JSON array extraction
                json_start = text.find('[')
                json_end = text.rfind(']')
                
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    text = text[json_start:json_end+1]
                
                questions = json.loads(text)
                if isinstance(questions, list) and len(questions) > 0:
                    valid_questions = []
                    for q in questions:
                        if all(k in q for k in ["question", "expected_points", "ideal_answer", "evaluation_criteria"]):
                            if q.get("question") and not q.get("question").startswith("Sample"):
                                valid_questions.append(q)
                    
                    if len(valid_questions) >= num_questions:
                        return valid_questions[:num_questions]
                    elif len(valid_questions) > 0:
                        # Pad with unique fallback questions to reach num_questions
                        while len(valid_questions) < num_questions:
                            needed = num_questions - len(valid_questions)
                            for fb_q in fallback_questions:
                                if fb_q["question"] not in [vq["question"] for vq in valid_questions]:
                                    valid_questions.append(fb_q)
                                    needed -= 1
                                    if needed == 0:
                                        break
                            # If we still need more (unlikely), break to prevent infinite loop and just return what we have or allow duplicates
                            if needed > 0:
                                break
                        
                        # If still not enough, only then multiply (fallback of fallback)
                        if len(valid_questions) < num_questions:
                            valid_questions = (valid_questions * (num_questions // len(valid_questions) + 1))[:num_questions]
                            
                        return valid_questions
            except Exception as e:
                prompt += "\n\nCRITICAL: RETURN ONLY RAW JSON ARRAY. NO MARKDOWN OR EXTRA TEXT."
        
        return fallback_questions

    def evaluate_answer(self, answer_obj: InterviewAnswer, language: str):
        if not answer_obj.transcript:
            return self._fallback_evaluation(answer_obj, "No transcript available to evaluate.")

        question_text = answer_obj.question.question_text
        interview_type = answer_obj.question.session.interview_type
        technology = answer_obj.question.session.technology
        difficulty = answer_obj.question.session.difficulty
        expected_points = answer_obj.question.expected_points_json
        ideal_answer = answer_obj.question.ideal_answer

        visual_context = ""
        if hasattr(answer_obj, 'visual_presence') and answer_obj.visual_presence:
            vp = answer_obj.visual_presence
            visual_context = f"""
        [VISUAL PRESENCE DATA]
        Eye Contact: {vp.eye_contact_pct}%
        Posture Score: {vp.posture_score}/100
        Expression Variety: {vp.expression_variety_score}/100
        Face Detected: {vp.face_detected_pct}%
        Evaluate their non-verbal communication based on this data. Include feedback in the suggestions.
        """

        prompt = f"""
        You are a highly strict, expert evaluator for a {difficulty} level {interview_type} interview.
        Topic: {technology}
        Question: "{question_text}"
        Expected Points: {expected_points}
        Ideal Answer: "{ideal_answer}"
        
        {visual_context}

        Candidate's Answer ({language}): "{answer_obj.transcript}"

        Evaluate this answer STRICTLY using the following rubric. YOU MUST QUOTE the transcript in your feedback to justify the scores.
        - Relevance (0-100): Does the answer directly address the question? (0-40 = off-topic, 41-70 = partial, 71-100 = full)
        - Technical Correctness (0-100): Are the technical claims factually correct? Penalize heavily for hallucinated facts.
        - Completeness (0-100): Did they hit the expected points? 
        - Clarity (0-100): Is the answer easy to follow?
        - Structure (0-100): Does it have a logical flow (e.g. STAR method for behavioral)?
        - Professionalism (0-100): Is the tone appropriate?

        If {interview_type} == "Technical" or "Coding":
        Overall Score = (Technical Correctness * 0.4) + (Completeness * 0.25) + (Relevance * 0.15) + (Clarity * 0.1) + (Structure * 0.1)
        If {interview_type} == "HR" or "Behavioral":
        Overall Score = (Relevance * 0.2) + (Completeness * 0.2) + (Structure * 0.2) + (Clarity * 0.2) + (Professionalism * 0.2)

        Return STRICTLY a JSON object with this exact structure:
        {{
            "overall_score": integer (0-100),
            "classification": "string (Correct, Partially Correct, Incorrect, or Not Answered)",
            "technical_correctness": integer,
            "concept_coverage": integer (represents completeness),
            "completeness": integer,
            "relevance": integer,
            "clarity": integer,
            "structure": integer,
            "professionalism": integer,
            "feedback": "string (Must include quotes from their transcript to justify your score)",
            "missing_points": ["string"],
            "correct_points": ["string"],
            "incorrect_points": ["string"],
            "suggestions": ["string"]
        }}
        """

        import logging
        import os
        from django.conf import settings
        logger = logging.getLogger(__name__)
        
        if not logger.handlers:
            log_path = os.path.join(settings.BASE_DIR, 'logs', 'ai_evaluation.log')
            fh = logging.FileHandler(log_path)
            fh.setLevel(logging.ERROR)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)

        logger.info("Interview AI evaluation started")
        
        data = None
        error_reasons = []

        # Provider 1: Gemini
        if self.client:
            logger.info("Attempting evaluation with Google Gemini")
            for attempt in range(2):
                try:
                    from google.genai import types  # type: ignore
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                        )
                    )
                    text = response.text.strip()
                    data = json.loads(text)
                    
                    # Plausibility sanity check
                    scores = [data.get(k, 0) for k in ["technical_correctness", "relevance", "clarity", "completeness"]]
                    if sum(scores) == 0 or len(set(scores)) == 1:
                        raise ValueError("Implausible identical or all-zero scores generated by Gemini.")
                    
                    data["evaluation_status"] = "EVALUATED"
                    data["feedback"] += "\n\n(Evaluated with Gemini 3.8 Flash)"
                    return data
                except Exception as e:
                    error_msg = str(e).lower()
                    logger.error(f"Gemini attempt {attempt + 1} failed: {str(e)}")
                    if "quota" in error_msg or "429" in error_msg or "403" in error_msg:
                        error_reasons.append("Gemini Quota/Auth Error")
                        break # Skip retries and move to next provider
                    error_reasons.append(f"Gemini Parse Error: {str(e)}")
                    prompt += "\n\nCRITICAL: YOUR PREVIOUS JSON WAS INVALID OR SCORES WERE IMPLAUSIBLE. ENSURE STRICT JSON COMPLIANCE."

        # Provider 2: OpenAI Fallback
        openai_key = getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        if openai_key and not data:
            logger.info("Attempting evaluation with OpenAI API (Fallback)")
            try:
                from openai import OpenAI  # type: ignore
                client = OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a strict technical interviewer and evaluator. Always output JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={ "type": "json_object" }
                )
                text = response.choices[0].message.content.strip()
                data = json.loads(text)
                
                scores = [data.get(k, 0) for k in ["technical_correctness", "relevance", "clarity", "completeness"]]
                if sum(scores) == 0 or len(set(scores)) == 1:
                    raise ValueError("Implausible identical or all-zero scores generated by OpenAI.")

                data["evaluation_status"] = "EVALUATED"
                data["feedback"] += "\n\n(Evaluated with OpenAI Fallback)"
                return data
            except Exception as e:
                logger.error(f"OpenAI fallback failed: {str(e)}")
                error_reasons.append(f"OpenAI Error: {str(e)}")
        
        # Provider 3: Offline Keyword Fallback
        return self._fallback_evaluation(answer_obj, f"AI Providers failed: {', '.join(error_reasons)}")

    def _fallback_evaluation(self, answer_obj=None, error_message="AI evaluation is temporarily unavailable."):
        if answer_obj and answer_obj.transcript:
            transcript = answer_obj.transcript.lower()
            try:
                expected_points = json.loads(answer_obj.question.expected_points_json)
            except:
                expected_points = []
                
            if not expected_points:
                expected_points = ["concept", "definition", "example", "practice"]

            matches = 0
            correct_points = []
            missing_points = []
            
            for pt in expected_points:
                keywords = [w for w in pt.lower().split() if len(w) > 3]
                if keywords and any(kw in transcript for kw in keywords):
                    matches += 1
                    correct_points.append(pt)
                else:
                    missing_points.append(pt)
                    
            concept_coverage = int((matches / max(len(expected_points), 1)) * 100)
            
            # Prevent 0 scores for long answers if they missed exact keywords
            word_count = len(transcript.split())
            if concept_coverage == 0 and word_count > 10:
                overall_score = min(50, word_count * 2)
            else:
                overall_score = concept_coverage
            
            classification = "Partially Correct" if overall_score > 0 else "Incorrect"
            if matches == len(expected_points) and matches > 0:
                classification = "Correct"
                
            suggestions = ["Try to elaborate more on the missing points to improve your offline score."]

            if hasattr(answer_obj, 'visual_presence') and answer_obj.visual_presence:
                vp = answer_obj.visual_presence
                if vp.eye_contact_pct < 60:
                    suggestions.append(f"Your eye contact was low ({vp.eye_contact_pct}%). Try looking at the camera more.")
                else:
                    suggestions.append(f"Good eye contact ({vp.eye_contact_pct}%). Keep it up!")

            return {
                "evaluation_status": "EVALUATED",
                "overall_score": overall_score,
                "classification": classification,
                "technical_correctness": overall_score,
                "concept_coverage": concept_coverage,
                "completeness": concept_coverage,
                "relevance": 50 if overall_score > 0 else 0,
                "clarity": 50,
                "structure": 50,
                "professionalism": 50,
                "feedback": f"Offline Fallback Evaluation active due to: {error_message} We used basic keyword matching to estimate your score.",
                "missing_points": missing_points,
                "correct_points": correct_points,
                "incorrect_points": [],
                "suggestions": suggestions
            }

        return {
            "evaluation_status": "FAILED",
            "overall_score": 0,
            "classification": "Not Evaluated",
            "technical_correctness": 0,
            "concept_coverage": 0,
            "completeness": 0,
            "relevance": 0,
            "clarity": 0,
            "structure": 0,
            "professionalism": 0,
            "feedback": error_message,
            "missing_points": [],
            "correct_points": [],
            "incorrect_points": [],
            "suggestions": []
        }

    def analyze_filler_words(self, transcript):
        filler_list = ["um", "uh", "like", "actually", "basically", "you know", "i mean", "so", "right"]
        count = 0
        words = transcript.lower().split()
        for w in words:
            clean_w = re.sub(r'[^a-z]', '', w)
            if clean_w in filler_list:
                count += 1
        return count
