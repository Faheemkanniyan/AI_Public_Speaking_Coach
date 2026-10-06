import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

headers = {"authorization": API_KEY}
audio_url = "https://assembly.ai/news.mp4"

payload = {
    "audio_url": audio_url,
    "language_detection": True,
    "disfluencies": True
}
res = requests.post("https://api.assemblyai.com/v2/transcript", json=payload, headers=headers)
print("Status:", res.status_code)
print("Response:", res.text)
