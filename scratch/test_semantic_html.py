import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from app.models import InterviewAnswer, InterviewQuestion, InterviewSession
from django.contrib.auth.models import User
from app.services.interview_service import InterviewService
import json

user, _ = User.objects.get_or_create(username='test_user_semantic')
session = InterviewSession.objects.create(
    user=user, interview_type="Technical", domain="Web Dev", technology="HTML", difficulty="Intermediate"
)
question = InterviewQuestion.objects.create(
    session=session,
    question_text="Explain semantic HTML.",
    expected_points_json='["Meaningful tags", "Accessibility", "SEO"]',
    ideal_answer="Semantic HTML introduces meaning to the web page rather than just presentation. For example, a <p> tag indicates that the enclosed text is a paragraph. This is both semantic and presentational."
)
answer = InterviewAnswer.objects.create(
    question=question,
    transcript="Semantic HTML is a main content in the web application. It's used to— we can design the web application uh like div syntax. Div is the main for the semantic HTML."
)

service = InterviewService()
result = service.evaluate_answer(answer, "English")
print("RESULT:")
print(json.dumps(result, indent=2))
