import os
import requests
from dotenv import load_dotenv

# 1. Load variables from local .env file into RAM
load_dotenv()

# 2. Retrieve secret key safely
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in .env file.")
    exit()

# 3. Clean Endpoint URL (No API key in the URL parameter!)
# Use the explicit model version instead of the alias
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"

# 4. Pass the API key securely inside Headers
headers = {
    "Content-Type": "application/json",
    "X-goog-api-key": api_key
}

# 5. Request Payload
prompt_text = "Explain why API key security is critical when pushing code to GitHub in 2 clear sentences."
payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

print("📡 Sending live HTTP POST request via Secure Header Authentication...")

try:
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    response.raise_for_status()

    # 6. Parse JSON Response
    data = response.json()
    ai_response = data["candidates"][0]["content"]["parts"][0]["text"]

    print("\n🤖 LIVE AI RESPONSE:")
    print("=" * 60)
    print(ai_response.strip())
    print("=" * 60)

except requests.exceptions.RequestException as err:
    print(f"\n❌ Network Error: {err}")