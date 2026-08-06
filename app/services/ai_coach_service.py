"""
AI Coach Chat Service for SpeakPro AI.
Provides real-time conversational public speaking advice and mentoring.
"""

import os
from django.conf import settings

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class AICoachService:
    """
    Conversational AI Assistant specializing in public speaking, executive communication,
    vocal presence, interview preparation, and reducing filler words.
    """

    def __init__(self):
        self.api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if self.api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception:
                self.model = None
        else:
            self.model = None

    def get_coach_response(self, user_message: str, user=None) -> str:
        """
        Returns a natural, motivating response to the user's coaching query.
        """
        if not user_message or not user_message.strip():
            return "Hello! I am SpeakPro AI, your personal Public Speaking Coach. What speaking challenge can I help you conquer today?"

        if self.model and self.api_key:
            try:
                prompt = f"""
                You are SpeakPro AI, a world-class Executive Communication and Public Speaking Coach.
                A student/speaker asks you:
                "{user_message}"

                Give a warm, actionable, highly practical response (in 3 to 4 concise paragraphs or clear bullet points)
                providing expert speaking advice, exercises, and encouragement. Keep it professional, modern, and motivating.
                """
                res = self.model.generate_content(prompt)
                return res.text.strip()
            except Exception:
                return self._fallback_coach_response(user_message)
        else:
            return self._fallback_coach_response(user_message)

    def _fallback_coach_response(self, query: str) -> str:
        """
        Intelligent offline conversational responses for common speaking questions.
        """
        q = query.lower()

        if "confidence" in q or "nervous" in q or "fear" in q or "anxious" in q:
            return (
                "**Building Unstoppable Stage Confidence:**\n\n"
                "1. **Reframe Nervousness as Excitement:** Your body produces adrenaline whether you feel scared or excited. Tell yourself *'I am excited to share this message'* before stepping up.\n"
                "2. **The 3-Second Rule:** Stand tall, plant your feet shoulder-width apart, make eye contact, and take a 3-second silent breath before speaking your first word.\n"
                "3. **Power Posing:** Practice confident physical posture for 2 minutes before speaking—research shows this reduces cortisol and boosts vocal projection."
            )
        elif "filler" in q or "um" in q or "uh" in q or "like" in q:
            return (
                "**Eliminating Filler Words ('Um', 'Uh', 'Like', 'You Know'):**\n\n"
                "1. **Embrace the Strategic Pause:** Filler words happen when your mouth works faster than your brain. Replace every urge to say 'um' with a 1-to-2 second silent pause. Silence sounds powerful and thoughtful to an audience.\n"
                "2. **Slow Down Your Tempo:** Speaking 10% slower gives your mind room to formulate the next sentence without gap-filling sounds.\n"
                "3. **Record and Catch Yourself:** Use SpeakPro AI's Practice mode daily to train your ear to recognize when fillers occur."
            )
        elif "fluent" in q or "fluency" in q or "flow" in q or "stutter" in q:
            return (
                "**Mastering Speech Fluency & Rhythm:**\n\n"
                "1. **Chunking Phrases:** Break your sentences into small 4-to-5 word rhythmic 'chunks' separated by short breaths.\n"
                "2. **Read Aloud Daily:** Spend 10 minutes every morning reading news or literature aloud, focusing on smooth transitions between paragraphs.\n"
                "3. **Use Signpost Words:** Transitions like *'Furthermore'*, *'Consequently'*, and *'Let's examine'* create logical bridges that keep your speech flowing effortlessly."
            )
        elif "interview" in q or "job" in q or "prepare" in q or "question" in q:
            return (
                "**Ace Your Professional Interviews:**\n\n"
                "1. **Use the STAR Method:** For behavioral questions, structure your answers with **S**ituation, **T**ask, **A**ction, and **R**esult.\n"
                "2. **Lead with the Headline:** Give a clear 1-sentence executive summary of your answer immediately, then dive into supporting evidence.\n"
                "3. **Vocal Authority:** Speak with a falling intonation at the end of statements rather than rising intonation, which can sound like you are asking for approval."
            )
        elif "pronunc" in q or "articulate" in q or "voice" in q or "accent" in q:
            return (
                "**Refining Pronunciation & Vocal Clarity:**\n\n"
                "1. **Over-Articulate Consonants:** Crisp 't', 'd', 'p', and 'k' sounds instantly make speech sound professional and intelligible.\n"
                "2. **Tongue Twister Warmups:** Warm up your articulators with phrases like *'Red leather, yellow leather'* for 2 minutes before speaking.\n"
                "3. **Vowel Resonance:** Open your jaw slightly wider on vowel sounds to create a fuller, warmer vocal resonance."
            )
        else:
            return (
                f"**Coaching Advice on '{query}':**\n\n"
                "Great question! In public speaking, clarity of thought leads to clarity of speech. "
                "Here is my top recommendation: always focus on **1 core takeaway message** you want your audience to remember. "
                "Support that message with strong vocal variety, purposeful pauses, and clear body language. "
                "Try practicing a 60-second speech on this topic in our Practice studio to get instant AI feedback!"
            )
