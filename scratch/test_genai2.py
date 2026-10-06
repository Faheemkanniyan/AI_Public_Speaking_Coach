import os
from google import genai

API_KEY = "YOUR_API_KEY"
client = genai.Client(api_key=API_KEY)

try:
    print("Testing gemini-3.8-flash with genai...")
    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents='Hello!'
    )
    print("Success with gemini-3.8-flash!", response.text)
except Exception as e:
    print("Failed with gemini-3.8-flash:", e)
