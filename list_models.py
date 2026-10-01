import sys
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()
filter = sys.argv[1].lower() if len(sys.argv) > 1 else "flash"

models = sorted(m.name.replace("models/", "") for m in client.models.list())
matched = [m for m in models if filter in m.lower()]

print(f"{len(matched)} models matching {filter!r} (of {len(models)} total):\n")
for name in matched:
    print(f"  {name}")
print("\nUse one as the backup in notes.py, or set it for a single run:")
print("  $env:GEMINI_MODEL = \"gemini-3.8-flash\"")
print("  .\\.venv\\Scripts\\python.exe notes.py lecture.vtt webdev")
