import sys, time
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

client = genai.Client()
args = sys.argv[1:]
probe = "--test" in args
args = [a for a in args if a != "--test"]
needle = args[0].lower() if args else "flash"

# Variants that cannot do text summarising: speech, images, and text-to-speech.
UNSUITABLE = ("tts", "image", "native-audio", "live")

all_models = sorted(m.name.replace("models/", "") for m in client.models.list())
matched = [
    m for m in all_models
    if needle in m.lower() and not any(bad in m.lower() for bad in UNSUITABLE)
]

print(f"{len(matched)} text models matching {needle!r} (of {len(all_models)} total)\n")

if not probe:
    for name in matched:
        print(f"  {name}")
    print("\nThis list shows what EXISTS, not what works. Retired models still appear here.")
    print(f"Run with --test to send a real request to each one:\n")
    print(f"  .\\.venv\\Scripts\\python.exe list_models.py {needle} --test")
    sys.exit(0)

usable, busy, retired = [], [], []
for name in matched:
    try:
        client.models.generate_content(model=name, contents="Say OK.")
        print(f"  usable   {name}")
        usable.append(name)
    except errors.APIError as e:
        if e.code in (503, 429):
            # Overloaded or throttled - it may well work later, so keep it.
            print(f"  busy     {name}  (error {e.code})")
            busy.append(name)
        elif e.code == 404:
            print(f"  RETIRED  {name}")
            retired.append(name)
        else:
            print(f"  broken   {name}  (error {e.code})")
    time.sleep(1)

print(f"\nusable: {len(usable)}  busy: {len(busy)}  retired: {len(retired)}")
if retired:
    print("Retired (never put these in notes.py): " + ", ".join(retired))

print("\nPaste this into notes.py, replacing FALLBACK_MODELS:\n")
print("FALLBACK_MODELS = [")
for name in usable + busy:
    print(f'    "{name}",')
print("]")
