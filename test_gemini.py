import os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("GEMINI_API_KEY")
print(f"1. GEMINI_API_KEY detected: {'YES (starts with ' + key[:6] + '...)' if key else 'NO (None)'}")

try:
    from google import genai
    print("2. SDK import: google-genai is INSTALLED")
    client = genai.Client(api_key=key)
    res = client.models.embed_content(
        model="text-embedding-004",
        contents="Hello world test"
    )
    print("3. API call status: SUCCESS!")
    print(f"   Vector length: {len(res.embeddings[0].values)}")
except Exception as e:
    print(f"3. API call status: FAILED -> {type(e).__name__}: {e}")
