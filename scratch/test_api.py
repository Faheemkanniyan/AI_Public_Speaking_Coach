import os
import google.generativeai as genai

API_KEY = "YOUR_API_KEY"
genai.configure(api_key=API_KEY)

try:
    model2 = genai.GenerativeModel("gemini-3.8-flash")
    print("Testing gemini-3.8-flash...")
    response = model2.generate_content("Hello!")
    print("Success with gemini-3.8-flash!", response.text)
except Exception as e:
    print("Failed with gemini-3.8-flash:", e)
