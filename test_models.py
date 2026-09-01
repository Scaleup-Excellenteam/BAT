import os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("GEMINI_API_KEY")
from google import genai

client = genai.Client(api_key=key)

print("Listing available embedding models for your key:")
found_models = []
try:
    for m in client.models.list():
        supported = getattr(m, "supported_actions", []) or getattr(m, "supported_generation_methods", [])
        name = getattr(m, "name", str(m))
        if "embed" in name.lower() or any("embed" in str(a).lower() for a in supported):
            print(f" - Found: {name}")
            found_models.append(name.replace("models/", ""))
except Exception as e:
    print(f"List error: {e}")

# Try testing candidates
candidates = found_models + ["text-embedding-004", "models/text-embedding-004", "embedding-001", "models/embedding-001"]
success = False
for cand in candidates:
    try:
        res = client.models.embed_content(model=cand, contents="test query")
        print(f"\n SUCCESS! Model '{cand}' works properly.")
        success = True
        break
    except Exception as err:
        print(f"Candidate '{cand}' failed: {err}")

if not success:
    print("\nCould not find a working embedding model.")
