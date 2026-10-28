"""Build checked-in original listening audio on macOS or Linux.

Use --sync in daily automation to create missing files and prune files no
longer referenced by the current season. The generated M4A files play offline.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
AUDIO = APP / "audio/season"


def synthesize(text: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as directory:
        folder = Path(directory)
        output = folder / "speech.m4a"
        if shutil.which("say") and shutil.which("afconvert"):
            source = folder / "speech.aiff"
            subprocess.run(["say", "-v", "Daniel", "-r", "165", "-o", str(source), text], check=True)
            subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(source), str(output)], check=True)
        elif shutil.which("espeak-ng") and shutil.which("ffmpeg"):
            source = folder / "speech.wav"
            subprocess.run(["espeak-ng", "-v", "en-gb", "-s", "155", "-w", str(source), text], check=True)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                            "-c:a", "aac", "-b:a", "96k", str(output)], check=True)
        else:
            raise RuntimeError("Audio synthesis needs macOS say/afconvert or Linux espeak-ng/ffmpeg")
        if output.stat().st_size < 1000:
            raise RuntimeError("Generated audio is empty")
        os.replace(output, destination)
    print(destination.relative_to(APP), destination.stat().st_size, "bytes")


def sync(content: dict, only_missing: bool) -> None:
    AUDIO.mkdir(parents=True, exist_ok=True)
    expected = {}
    for item in content["listening"]:
        if len(item["sentences"]) != len(item["sentenceAudio"]):
            raise ValueError(f"Sentence audio count differs for {item['id']}")
        expected[APP / item["audio"]] = " ".join(item["sentences"])
        expected.update((APP / audio, sentence) for audio, sentence in zip(item["sentenceAudio"], item["sentences"]))
    if not all(path.resolve().is_relative_to(AUDIO.resolve()) for path in expected):
        raise ValueError("Audio path is outside app/audio/season")
    for path, text in expected.items():
        if not only_missing or not path.is_file():
            synthesize(text, path)
    if only_missing:
        for path in AUDIO.glob("*.m4a"):
            if path not in expected:
                path.unlink()
                print("removed", path.relative_to(APP))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="create missing files and remove stale current-season files")
    args = parser.parse_args()
    content = json.loads((APP / "data/season-content.json").read_text(encoding="utf-8"))
    sync(content, args.sync)


if __name__ == "__main__":
    main()
