import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

import google.generativeai as genai
from django.conf import settings
import json

api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

prompt = """
Question: Explain semantic HTML.
Answer: Semantic HTML means using HTML elements that clearly describe the meaning and purpose of the content.

Evaluate the answer. Return STRICTLY JSON containing:
{
    "overall_score": 0,
    "technical_accuracy": 0,
    "concept_coverage": 0,
    "completeness": 0,
    "relevance": 0,
    "clarity": 0,
    "classification": "",
    "correct_points": [],
    "missing_points": [],
    "incorrect_points": [],
    "feedback": "",
    "ideal_answer": "",
    "improvement_suggestions": []
}
"""

try:
    response = model.generate_content(prompt)
    print("RAW OUTPUT:")
    print(response.text)
    
    text = response.text.strip()
    json_start = text.find('{')
    json_end = text.rfind('}')
    
    if json_start != -1 and json_end != -1 and json_end > json_start:
        text = text[json_start:json_end+1]
    
    data = json.loads(text)
    print("JSON PARSED SUCCESSFULLY:")
    print(json.dumps(data, indent=2))
except Exception as e:
    print("FAILURE! Exception:")
    import traceback
    traceback.print_exc()
