import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Loads your .env file

url = os.getenv("LLM_ENDPOINT") + "/chat/completions"
api_key = os.getenv("LLM_API_KEY")

payload = {
    "model": "qwen3-coder:latest",  # Or whatever model they told you to use
    "messages": [{"role": "user", "content": "Reply with exactly one word: 'Hello'."}],
}

headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

print("Sending authenticated request to Hactar...")
response = requests.post(url, json=payload, headers=headers, timeout=60.0)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
