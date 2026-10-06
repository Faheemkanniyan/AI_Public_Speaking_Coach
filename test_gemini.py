import os
import google.generativeai as genai
import json

genai.configure(api_key='YOUR_API_KEY')
model = genai.GenerativeModel('gemini-3.6-flash')
prompt = """
You are an expert, senior-level interviewer in the "IT" domain.
Your task is to generate 5 highly specific, realistic Intermediate level Technical interview questions.
The questions must be deeply tailored to the topic/technology: "HTML".

Guidelines based on Interview Type:
- If "Technical": Focus heavily on complex problem-solving, architectural choices, debugging, deep conceptual understanding, and practical scenarios related to "HTML". Avoid generic definitions.

The questions MUST be in English and feel like they are asked by a rigorous hiring manager.

Return the result strictly as a JSON list of strings, like this:
["Question 1", "Question 2", ...]
Do NOT include any markdown, formatting, or extra text.
"""
try:
    response = model.generate_content(prompt)
    print("RAW RESPONSE:")
    print(repr(response.text))
    
    text = response.text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    questions = json.loads(text)
    print("PARSED JSON:")
    print(questions)
except Exception as e:
    print("Exception:", e)
