"""Create sentence clips for the original listening review (macOS build step)."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
DATA = APP / "data" / "listening-test.json"
OUT = APP / "audio" / "sentences"


def split_sentences(transcript: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-Z])", transcript) if part.strip()]


def build_clip(job: tuple[str, str]) -> None:
    relative, sentence = job
    target = APP / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ielts-sentence-") as temporary:
        aiff = Path(temporary) / "voice.aiff"
        m4a = Path(temporary) / "voice.m4a"
        subprocess.run(["say", "-v", "Daniel", "-r", "165", "-o", str(aiff), sentence], check=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(m4a)], check=True)
        if m4a.stat().st_size < 2000:
            raise RuntimeError(f"empty sentence audio: {relative}")
        target.write_bytes(m4a.read_bytes())


def main() -> None:
    bank = json.loads(DATA.read_text(encoding="utf-8"))
    jobs = []
    for section in bank["sections"]:
        sentences = []
        for number, sentence in enumerate(split_sentences(section["transcript"]), 1):
            relative = f"audio/sentences/{section['id'].lower()}-{number:03}.m4a"
            sentences.append({"number": number, "text": sentence, "audio": relative})
            jobs.append((relative, sentence))
        section["sentences"] = sentences
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(build_clip, jobs))
    DATA.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"created {len(jobs)} sentence clips")


if __name__ == "__main__":
    main()
