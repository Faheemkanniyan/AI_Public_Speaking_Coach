import os
from dotenv import load_dotenv
load_dotenv()
from google import genai

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
models = client.models.list()

for model in models:
    if 'generateContent' in model.supported_actions:
        try:
            print(f"Testing {model.name}...")
            response = client.models.generate_content(
                model=model.name,
                contents="hello"
            )
            print(f"SUCCESS: {model.name} -> {response.text}")
            break
        except Exception as e:
            pass
