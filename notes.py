import os, sys, re, time, pathlib
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

PROMPTS = {
    "webdev": """Turn this web development lecture transcript into clean study notes in markdown.
- Use headings for each topic
- Beginner-friendly explanations, short and clear
- Put every code example in a fenced code block with the language tag
- After each code block, explain what it does in 1-2 sentences
- Define new terms in a 'Key terms' section
- Remove filler and repetition
- End with a 'Key takeaways' list

Transcript:
""",
    "infoman": """Turn this Information Management (databases) lecture transcript into clean study notes in markdown.
- Use headings for each topic
- Very beginner-friendly: assume this is the first time learning databases
- Include visual examples as Mermaid diagrams (```mermaid blocks), e.g. erDiagram for ERDs and relationships, flowchart for processes
- Include small example tables in markdown to show sample data
- Put SQL in fenced ```sql blocks and explain each query in plain words
- Define new terms in a 'Key terms' section
- Remove filler and repetition
- End with a 'Key takeaways' list

Transcript:
""",
}

def clean_vtt(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")) or line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if not out or out[-1] != line:
            out.append(line)
    return " ".join(out)

if len(sys.argv) < 3:
    sys.exit(f"Usage: python notes.py <transcript.vtt> <{'|'.join(PROMPTS)}>")

path = pathlib.Path(sys.argv[1])
subject = sys.argv[2]
if subject not in PROMPTS:
    sys.exit(f"Unknown subject {subject!r}. Choose one of: {', '.join(PROMPTS)}")
if not path.is_file():
    sys.exit(f"No such file: {path}")

raw = path.read_text(encoding="utf-8")
transcript = clean_vtt(raw) if path.suffix == ".vtt" else raw

client = genai.Client()

# Models to try in order. Set GEMINI_MODEL to pin one model and skip the fallbacks.
# Verified with: .\.venv\Scripts\python.exe list_models.py flash --test
# Do NOT add gemini-2.5-flash or gemini-2.5-flash-lite: both are retired and return 404.
FALLBACK_MODELS = [
    "gemini-flash-latest",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-omni-flash-preview",
]
MODELS = [os.environ["GEMINI_MODEL"]] if os.environ.get("GEMINI_MODEL") else FALLBACK_MODELS

def generate(prompt):
    for model in MODELS:
        for attempt in range(5):
            try:
                text = client.models.generate_content(model=model, contents=prompt).text
            except errors.APIError as e:
                if e.code == 429:
                    # Rate limited: this model still works, just wait it out.
                    wait = 15 * (attempt + 1)
                    print(f"{model}: rate limited, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                if e.code in (404, 500, 503):
                    # 404 = model retired, 500/503 = overloaded. Either way, use the next model.
                    print(f"{model}: error {e.code}, trying the next model...")
                    break
                raise
            if text:
                return text
            print(f"{model}: empty response, trying the next model...")
            break
    raise RuntimeError(f"All models failed ({', '.join(MODELS)}). Try again in a few minutes.")

out_path = path.with_suffix(".md")
out_path.write_text(generate(PROMPTS[subject] + transcript), encoding="utf-8")
print(f"Saved {out_path}")
