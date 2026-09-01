import os, traceback
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    from google import genai
    client = genai.Client(api_key=api_key)

    print("1. Testing Generation (gemini-3.6-flash)...")
    gen_res = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Say hello in one word"
    )
    print("Generation result:", gen_res.text.strip() if gen_res.text else "None")

    print("\n2. Testing Embedding (gemini-embedding-001)...")
    emb_res = client.models.embed_content(
        model="gemini-embedding-001",
        contents="Hello world"
    )
    vals = emb_res.embedding.values if hasattr(emb_res, "embedding") else emb_res.embeddings[0].values
    print("Embedding success! Length:", len(vals))

except Exception:
    traceback.print_exc()
