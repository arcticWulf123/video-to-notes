import subprocess, pathlib, time, sys
YTDLP = [sys.executable, "-m", "yt_dlp"]
COOKIE_ARGS = ["--cookies", "cookies.txt"]
subject = sys.argv[1]                                # webdev or infoman
week = sys.argv[2] if len(sys.argv) > 2 else "week"  # e.g. week5

OUT = pathlib.Path("lectures") / subject
OUT.mkdir(parents=True, exist_ok=True)

urls = [u.strip() for u in open(f"urls_{subject}.txt") if u.strip()]

whisper = None  # loaded only if needed

for i, url in enumerate(urls, 1):
    name = f"{subject}_{week}_lec{i}"
    print(f"\n=== {name} ===")
    if (OUT / f"{name}.md").exists() or (OUT / f"{name}.en.md").exists():
        print("Already done, skipping.")
        continue
    # Try captions first (fast)
    subprocess.run([
        *YTDLP, "--write-auto-subs", "--sub-langs", "en",
        "--skip-download", *COOKIE_ARGS,
        "-o", str(OUT / name), url,
    ])
    vtt = OUT / f"{name}.en.vtt"

    if vtt.exists():
        source = vtt
    else:
        # No captions: download audio and transcribe with Whisper
        subprocess.run([
            *YTDLP, "-x", "--audio-format", "mp3",
            *COOKIE_ARGS,
            "-o", str(OUT / f"{name}.%(ext)s"), url,
        ])
        if whisper is None:
            from faster_whisper import WhisperModel
            whisper = WhisperModel("small", compute_type="int8")
        segments, _ = whisper.transcribe(str(OUT / f"{name}.mp3"))
        source = OUT / f"{name}.txt"
        source.write_text(" ".join(s.text for s in segments), encoding="utf-8")

    subprocess.run([sys.executable, "notes.py", str(source), subject])
    time.sleep(10)  # stay under free-tier rate limits

print(f"\nDone. Check lectures/{subject}/")
