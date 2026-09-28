import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from app.models import InterviewAnswer, InterviewQuestion, InterviewSession
from django.contrib.auth.models import User
from app.services.interview_service import InterviewService

user, _ = User.objects.get_or_create(username='test_user')
session = InterviewSession.objects.create(
    user=user, interview_type="Technical", domain="Web Dev", technology="HTML", difficulty="Intermediate"
)
question = InterviewQuestion.objects.create(
    session=session,
    question_text="Explain HTML forms and validation.",
    expected_points_json='["Forms collect user data", "Validation checks data", "required attribute"]',
    ideal_answer="HTML forms collect user input. Validation ensures data is correct using attributes like required."
)
answer = InterviewAnswer.objects.create(
    question=question,
    transcript="HTML forms and validation actually used for collecting the details from the users, for example password, name, email."
)

service = InterviewService()
result = service.evaluate_answer(answer, "English")
print("RESULT:")
import json
print(json.dumps(result, indent=2))
