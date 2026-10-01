import os, sys, re, time, pathlib
from google import genai
from google.genai import errors

PROMPTS = {
    "webdev": """Turn this web development lecture transcript into clean study notes in markdown.
- Use headings for each topic
- Beginner-friendly explanations, short and clear
- Put every code example in a fenced code block with the language tag
- After each code block, explain what it does in 1-2 sentences
- Define new terms in a 'Key terms' section
- Remove filler and repetition
- 
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
        if not line or "-->" in line or line.startswith(("WEBVTT", "NOTE")) or line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if not out or out[-1] != line:
            out.append(line)
    return " ".join(out)

path = pathlib.Path(sys.argv[1])
subject = sys.argv[2]
raw = path.read_text(encoding="utf-8")
transcript = clean_vtt(raw) if path.suffix == ".vtt" else raw

client = genai.Client()

# Models to try in order. Add a second flash model from list_models.py as a backup.
MODELS = [os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")]

def generate(prompt):
    for model in MODELS:
        for attempt in range(5):
            try:
                return client.models.generate_content(model=model, contents=prompt).text
            except errors.APIError as e:
                if e.code in (429, 500, 503):
                    wait = 15 * (attempt + 1)
                    print(f"{model}: error {e.code}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
    raise RuntimeError("Gemini is busy. Try again in a few minutes.")

out_path = path.with_suffix(".md")
out_path.write_text(generate(PROMPTS[subject] + transcript), encoding="utf-8")
print(f"Saved {out_path}")
