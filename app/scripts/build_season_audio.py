"""Generate bundled original seasonal listening audio on macOS.

The checked-in M4A files play on any platform; this script is only for editors.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
content = json.loads((APP / "data/season-content.json").read_text(encoding="utf-8"))


def synthesize(text: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "speech.aiff"
        subprocess.run(["say", "-v", "Daniel", "-r", "165", "-o", str(source), text], check=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(source), str(destination)], check=True)
    print(destination.relative_to(APP), destination.stat().st_size, "bytes")


for item in content["listening"]:
    synthesize(" ".join(item["sentences"]), APP / item["audio"])
    assert len(item["sentences"]) == len(item["sentenceAudio"])
    for sentence, audio in zip(item["sentences"], item["sentenceAudio"]):
        synthesize(sentence, APP / audio)
