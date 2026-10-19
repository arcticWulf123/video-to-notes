# Lecture Notes Generator

Turns recorded lecture videos into clean, beginner-friendly markdown study notes.

It downloads each video, grabs its transcript (or transcribes the audio when captions
don't exist), then asks the Gemini API to rewrite that transcript into structured notes.
No manual copy-pasting, no watching the video twice.

---

## How it works

```
urls_<subject>.txt          cookies.txt (your YouTube login, for age-restricted videos)
      │                             │
      ▼                             ▼
    batch.py ──────► yt-dlp ───► lecture.en.vtt   captions exist?  (fast path)
      │                             │
      │  no captions               ▼
      │  ────────────► faster-whisper ──► lecture.txt
      │                             │
      │                             ▼
      └──► notes.py ──► clean_vtt() ──► Gemini API ──► lecture.md
               │
               └─ prompt template from PROMPTS[subject]
```

Two ways in:

| Script | What it does |
|---|---|
| `notes.py` | **One** transcript → one `.md`. No downloads, no YouTube. |
| `batch.py` | **Many** videos end to end: fetch, transcribe, write notes. Skips what's already done. |

---

## Requirements

- **Python 3.9+** (developed on 3.14)
- A **free Gemini API key** — <https://aistudio.google.com/apikey>
- A **`cookies.txt`** (Netscape-format), if any videos are age-restricted

Everything else installs itself.

---

## Setup

**1. Open a terminal in the project folder.** Every command below assumes you're in
the directory containing `notes.py` — `batch.py` reads its URL lists by relative path.

```powershell
cd path\to\lecture_notes
```

**2. Create the virtual environment.** A virtual environment (`.venv`) is a private,
isolated copy of Python and its packages, so installing this project can't break
anything else on your machine.

```powershell
python -m venv .venv
```

**3. Activate it.** You do this once per terminal session:

```powershell
.\.venv\Scripts\Activate.ps1
```

Your prompt gains a `(.venv)` prefix. To deactivate later, just run `deactivate`.

> If PowerShell blocks this with an "execution policy" error, either use
> `.\.venv\Scripts\python.exe` instead of `python` for every command below, or run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

**4. Install the dependencies.**

```powershell
pip install -r requirements.txt
```

**5. Create your `.env`.** Copy the example and paste in your key:

```powershell
Copy-Item .env.example .env
notepad .env
```

```ini
GEMINI_API_KEY=your_key_here
```

`.env` is already in `.gitignore`, so your key can never be committed by accident.

---

## Usage

> If you skipped activation, replace `python` with `.\.venv\Scripts\python.exe`.

### One transcript → notes

```powershell
python notes.py <transcript.vtt> <subject>
```

```powershell
python notes.py test.en.vtt webdev
```

Writes `test.md` next to the input. Fastest way to try things, and costs one API call.

### A whole batch of lectures

```powershell
python batch.py <subject> [week]
```

```powershell
python batch.py webdev week9
```

| Argument | Required | Notes |
|---|---|---|
| `subject` | yes | `webdev` or `infoman` — must match an existing `urls_<subject>.txt` |
| `week` | no | Just a label in the filename. Defaults to `week`. |

`batch.py` **skips any lecture whose `.md` already exists**, so it's always safe to
re-run after a crash or a network drop. Press `Ctrl+C` to stop partway.

### See which models are available

```powershell
python list_models.py               # every flash model your key can reach
python list_models.py pro           # filter by any substring
python list_models.py flash --test  # actually call each one and report which work
```

Add `--test` when a model starts failing. `models.list()` reports what **exists in the
catalogue**, which is not the same as what your key can **use** — retired models keep
appearing in the list. `--test` sends one tiny request per model and prints a ready-to-paste
`FALLBACK_MODELS` block, excluding anything that returns `404`.

---

## Configuration

Everything configurable lives in `.env`. It wins over nothing and loses to nothing —
it simply populates environment variables, which the scripts read.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GEMINI_API_KEY` | **yes** | — | Your Gemini key. Without it you get an auth error. |
| `GEMINI_MODEL` | no | six-model fallback list | Pin one model and skip the fallbacks. |

```ini
# .env
GEMINI_API_KEY=your_key_here

# Optional: skip model fallback entirely
GEMINI_MODEL=gemini-3.6-flash
```

To change the model for a *single run* without editing `.env`:

```powershell
$env:GEMINI_MODEL = "gemini-3.1-flash-lite"
python notes.py lecture.vtt webdev
```

### Adding a subject

1. Add a prompt template to `PROMPTS` in `notes.py:8`, keyed by your new subject name.
2. Create `urls_<subject>.txt` in the project root — one video URL per line.
3. Run `python batch.py <subject> week1`.

### Tuning the output

The prompt templates at the top of `notes.py` are plain text. Edit the bullet points to
change the structure, tone, or what gets emphasised. This is the main knob for
controlling output quality.

### The video list

`urls_<subject>.txt`, one URL per line. Blank lines are ignored. The Nth URL becomes
lecture N:

```
https://www.youtube.com/watch?v=aaaaaaaaaaa
https://www.youtube.com/watch?v=bbbbbbbbbbb
```

---

## Files

| File | Role |
|---|---|
| `notes.py` | Cleans a transcript and asks Gemini to turn it into notes. |
| `batch.py` | Loops over URLs: downloads, transcribes, calls `notes.py`. |
| `list_models.py` | Lists models your API key can reach. `--test` also calls each one. |
| `requirements.txt` | The four Python packages this needs. |
| `.env` | Your API key. Gitignored. |
| `.env.example` | Template for `.env`. Safe to commit. |
| `cookies.txt` | YouTube login cookies. Gitignored. **Treat as a password.** |
| `urls_*.txt` | Video lists. Gitignored. |
| `lectures/` | Generated notes. Gitignored. |

### How `notes.py` fits together

| Line | What happens |
|---|---|
| `8` | `PROMPTS` — one instruction template per subject |
| `34` | `clean_vtt()` — strips timestamps, cue numbers, and `<00:00:01>` tags from a subtitle file |
| `56` | Runs `clean_vtt()` only if the input is `.vtt`; plain text passes through |
| `58` | `genai.Client()` reads `GEMINI_API_KEY` from the environment automatically |
| `63` | `FALLBACK_MODELS` — tried top to bottom |
| `78` | `generate()` — the retry and fallback loop |
| `102` | Writes the result to the same filename with a `.md` extension |

### The retry logic

This is the part worth understanding. Gemini returns failure codes that look
similar but need opposite responses:

| Code | Meaning | Response |
|---|---|---|
| **429** | You're sending too fast | Same model is fine. Wait `15s × attempt`, retry up to 5 times. |
| **500 / 503** | That model is overloaded | Waiting won't help. **Switch to the next model immediately.** |
| **404** | That model has been retired | Same as above — **switch to the next model.** Never add a `404` model back to the list. |
| other | Real bug | Raise — don't silently retry something that won't fix itself. |

That distinction matters. An earlier version retried 503s five times, burning ~4
minutes per lecture before giving up — and because only one model was configured,
there was nothing to fall back to. The current version falls through the list in
seconds. If you see this in the output, it's working as intended:

```
gemini-3.8-flash: error 503, trying the next model...
```

`404` was originally treated as a "real bug" and raised, which meant one retired
model in the list could crash a whole batch once the working models were briefly
overloaded. Google retires models on a rolling basis, so it is now handled like a
`503`: skip it and try the next one.

### `cookies.txt`

Exported from a browser while logged into YouTube (a "Get cookies.txt LOCALLY"
extension works well). It only matters for age-restricted or members-only videos.

**This file grants access to your YouTube account. Treat it like a password** — never
commit it, never paste it in chat. It's in `.gitignore`; if you ever add it to git by
hand, rotate your YouTube password.

---

## Output

Notes land in `lectures/<subject>/`, named `<subject>_<week>_lec<N>.md`:

```
lectures/
└── webdev/
    ├── webdev_week8_lec1.en.md
    ├── webdev_week8_lec1.en.vtt
    └── ...
```

The `.en` in the name means the notes came from English captions. Notes generated from
Whisper transcription have no `.en`, because there were no captions to begin with.

> **Heads up:** `lectures/` is gitignored, so your notes are **not** backed up by git.
> Copy them somewhere safe, or drop that line from `.gitignore` if you want them in
> version control.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'yt_dlp'` | Dependencies not installed, or venv not active | `pip install -r requirements.txt` |
| `No urls_webdev.txt here.` | Wrong directory | `cd` to the project root and retry |
| `Unknown subject 'foo'` | Typo in the subject name | Use `webdev` or `infoman` |
| `All models failed (...)` | Every model overloaded | Wait a few minutes, rerun. `python list_models.py flash --test` to see what's up |
| `trying the next model...` | Normal. One model was busy | Nothing to do |
| `ModuleNotFoundError: No module named 'dotenv'` | You ran system `python`, not the venv | Use `.\.venv\Scripts\python.exe batch.py ...` |
| `404 NOT_FOUND` on a model | That model was retired by Google | Should no longer be fatal; run `list_models.py flash --test` and refresh `FALLBACK_MODELS` |
| Auth / 400 error from Gemini | Missing or wrong `GEMINI_API_KEY` | Check `.env`, then `python list_models.py` |
| yt-dlp login prompts or "Sign in" pages | `cookies.txt` expired | Re-export from a logged-in browser |
| `RuntimeError` but no traceback above it | A lecture failed | Read the `FAILED (...)` line above it — it names the cause |
| Notes suddenly stop in the middle | Free-tier quota hit | Wait for the daily reset, or use a `flash-lite` model |

### Re-generating one lecture

Delete its `.md` and re-run `batch.py` — the skip logic will pick it up again:

```powershell
Remove-Item lectures\webdev\webdev_week9_lec3.en.md
python batch.py webdev week9
```

### Known cosmetic warning

`google-genai` prints this on every call:

```
Direct use of automatic function calling (AFC) in Models.generate_content is not
recommended. Instead, we recommend to use AFC in Chat.send_message.
```

Harmless today — the call still works. It just means a future library release will
require switching `notes.py:76` from `client.models.generate_content(...)` to
`client.chats.create(...).send_message(...)`. No action needed unless it ever becomes
an error.

---

## Cost and rate limits

Built for Gemini's **free tier**. `batch.py` sleeps 10 seconds between lectures
(`batch.py:66`) to stay under the free-tier request rate. One lecture is roughly one
API call, so a full week of five lectures costs about five calls.

Output quality tracks the model: the `flash` models in `FALLBACK_MODELS` are fast and
free. To upgrade to a `pro` model, list what's available and pin one:

```powershell
python list_models.py pro
```

```
  gemini-2.5-pro
  gemini-3.1-pro-preview
  gemini-pro-latest
  ...
```

```powershell
$env:GEMINI_MODEL = "gemini-pro-latest"
python notes.py lecture.vtt webdev
```

Pro models bill per token. They're also slower and rate-limited harder on the free
tier, so expect retries — the 429 handling in `generate()` covers this.
