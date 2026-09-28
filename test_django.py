import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from app.services.interview_service import InterviewService
import google.generativeai as genai

print(f"GENAI_AVAILABLE: {genai is not None}")
service = InterviewService()
print(f"API_KEY: {service.api_key}")
print(f"MODEL: {service.model}")
if not service.model:
    print("MODEL IS NONE! WHY?")

questions = service._generate_questions("Technical", "IT", "HTML", "Intermediate", 5, "en-US")
print(f"QUESTIONS: {questions}")
