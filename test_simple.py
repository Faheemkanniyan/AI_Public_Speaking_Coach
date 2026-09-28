import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

import google.generativeai as genai
from django.conf import settings

api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
print("API Key configured:", bool(api_key))

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

try:
    response = model.generate_content("Explain HTML in one sentence.")
    print("SUCCESS! Output:")
    print(response.text)
except Exception as e:
    print("FAILURE! Exception:")
    print(e)
