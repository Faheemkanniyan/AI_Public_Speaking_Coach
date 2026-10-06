import os
from dotenv import load_dotenv
load_dotenv()
from google import genai

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
models = client.models.list()

for model in models:
    if 'generateContent' in model.supported_generation_methods:
        try:
            print(f"Testing {model.name}...")
            response = client.models.generate_content(
                model=model.name,
                contents="Say hello"
            )
            print(f"SUCCESS: {model.name} -> {response.text}")
        except Exception as e:
            print(f"ERROR: {model.name} -> {str(e)}")
