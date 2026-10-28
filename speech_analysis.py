"""Optional local transcription and timing evidence for recorded speaking practice."""
from __future__ import annotations

import importlib.util
import os
import tempfile
from functools import lru_cache
from pathlib import Path

MAX_AUDIO_BYTES = 15 * 1024 * 1024
MAX_AUDIO_SECONDS = 300
SUFFIXES = {"audio/webm": ".webm", "audio/mp4": ".mp4", "audio/ogg": ".ogg",
            "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/mpeg": ".mp3"}


def speech_available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


@lru_cache(maxsize=1)
def speech_model():
    if not speech_available():
        raise RuntimeError("未安装本地语音转写组件；请运行 pip install -r requirements-speech.txt")
    # Direct HTTPS avoids a stalled Xet transfer on some local networks.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    from faster_whisper import WhisperModel

    return WhisperModel(os.environ.get("IELTS_WHISPER_MODEL", "base.en"),
                        device="cpu", compute_type="int8")


def transcribe_audio(data: bytes, mime: str) -> dict:
    """Return transcript and approximate timing measurements; raw audio stays local."""
    media_type = mime.split(";", 1)[0].strip().lower()
    suffix = SUFFIXES.get(media_type)
    if not suffix:
        raise ValueError("不支持的录音格式")
    if not 1 <= len(data) <= MAX_AUDIO_BYTES:
        raise ValueError("录音须小于 15 MB")
    with tempfile.TemporaryDirectory(prefix="ielts-speech-") as directory:
        path = Path(directory) / f"recording{suffix}"
        path.write_bytes(data)
        try:
            segments, info = speech_model().transcribe(str(path), language="en",
                                                        word_timestamps=True, vad_filter=True)
            segments = list(segments)
        except RuntimeError:
            raise
        except Exception as exc:
            raise ValueError("录音无法解码或转写，请重新录制") from exc
    duration = float(info.duration or max((segment.end for segment in segments), default=0))
    if duration > MAX_AUDIO_SECONDS:
        raise ValueError("录音请控制在 5 分钟以内")
    if duration < 2:
        raise ValueError("录音太短，请录制完整的英文回答")
    transcript = " ".join(segment.text.strip() for segment in segments).strip()
    if len(transcript) < 40:
        raise ValueError("录音转写内容太短；请录制更完整的英文回答（至少约 40 字符）")
    if len(transcript) > 8000:
        raise ValueError("录音转写内容过长，请缩短回答")
    words = [word for segment in segments for word in (segment.words or [])]
    spoken_seconds = sum(max(0, float(segment.end) - float(segment.start)) for segment in segments)
    gaps = [max(0, float(current.start) - float(previous.end))
            for previous, current in zip(words, words[1:])]
    word_count = len(transcript.split())
    return {
        "transcript": transcript,
        "durationSeconds": round(duration, 1),
        "speechSeconds": round(spoken_seconds, 1),
        "wordCount": word_count,
        "wordsPerMinute": round(word_count * 60 / spoken_seconds) if spoken_seconds > 0 else None,
        "pauseCount": sum(gap >= 0.6 for gap in gaps) if words else None,
        "longPauseCount": sum(gap >= 1.5 for gap in gaps) if words else None,
    }
