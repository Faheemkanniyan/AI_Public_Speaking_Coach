import os, sys, django, json
sys.path.insert(0, ".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from google import genai
from google.genai import types

c = genai.Client(api_key=settings.GEMINI_API_KEY)
cfg = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)

prompt = """You are an interview evaluator. Evaluate this candidate answer:
Question: "Explain Python generators and yield"
Candidate Answer: "statement and how they optimise memory also"

Return JSON with:
{
  "overall_score": 10,
  "classification": "Incorrect",
  "feedback": "...",
  "relevance_score": 10,
  "technical_correctness_score": 0,
  "completeness_score": 0,
  "structure_score": 0,
  "communication_score": 10,
  "relevance_evidence": {"quotes": ["..."], "reason": "..."},
  "technical_correctness_evidence": {"quotes": ["..."], "reason": "..."},
  "completeness_evidence": {"quotes": ["..."], "reason": "..."},
  "structure_evidence": {"quotes": ["..."], "reason": "..."},
  "communication_evidence": {"quotes": ["..."], "reason": "..."},
  "missing_points": ["point 1", "point 2"],
  "incorrect_statements": [],
  "correct_points": [],
  "suggestions": ["..."],
  "model_answer": "..."
}
"""

try:
    r = c.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=cfg
    )
    print("SUCCESS on gemini-3.5-flash-lite!")
    print(r.text[:500])
except Exception as e:
    print("FAILED on gemini-3.5-flash-lite:", e)
