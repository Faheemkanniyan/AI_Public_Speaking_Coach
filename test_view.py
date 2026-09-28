import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from app.models import InterviewSession, InterviewQuestion, InterviewAnswer

user, _ = User.objects.get_or_create(username='test_user')
user.set_password('password')
user.save()

# create session and question
session = InterviewSession.objects.create(
    user=user, interview_type="Technical", domain="Web Dev", technology="HTML", difficulty="Intermediate", interview_language="English"
)
question = InterviewQuestion.objects.create(
    session=session,
    question_text="Explain HTML forms and validation.",
    expected_points_json='["Forms collect user data", "Validation checks data", "required attribute"]',
    ideal_answer="HTML forms collect user input. Validation ensures data is correct using attributes like required."
)
answer = InterviewAnswer.objects.create(
    question=question,
    transcript="HTML forms and validation actually used for collecting the details from the users, for example password, name, email.",
    answer_status="ANSWERED"
)
from app.models import InterviewFeedback
feedback = InterviewFeedback.objects.create(
    answer=answer,
    evaluation_status="FAILED"
)

client = Client()
client.login(username='test_user', password='password')
response = client.get(f'/interview/{session.id}/question/{question.id}/retry-feedback/')

print("STATUS CODE:", response.status_code)
if response.status_code == 302:
    print("Redirected to:", response.url)
