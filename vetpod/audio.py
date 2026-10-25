"""Synthèse vocale (Microsoft Edge TTS, gratuit) et assemblage MP3 avec ffmpeg."""
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path


async def _tts(text: str, voice: str, rate: str, path: Path):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def synthesize(segments: list[dict], voices: list[str], rate: str, out_mp3: Path, work: Path) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg est requis pour assembler l'épisode (https://ffmpeg.org).")
    parts_dir = work / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    silence = parts_dir / "silence.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono", "-t", "0.6", "-c:a", "libmp3lame", "-b:a", "48k", str(silence)], check=True)
    files = []
    for i, seg in enumerate(segments):
        p = parts_dir / f"{i:04d}.mp3"
        voice = voices[seg.get("speaker", 0) % len(voices)]
        for attempt in range(3):
            try:
                asyncio.run(_tts(seg["text"], voice, rate, p))
                break
            except Exception:
                if attempt == 2:
                    raise
        files += [p, silence]
    lst = parts_dir / "list.txt"
    lst.write_text("".join(f"file '{f.resolve()}'\n" for f in files))
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-ar", "44100", "-ac", "1", "-b:a", "96k", "-af", "loudnorm=I=-16:TP=-1.5",
                    str(out_mp3)], check=True)
    shutil.rmtree(parts_dir, ignore_errors=True)
    return out_mp3


def duration_seconds(mp3: Path) -> int:
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                            "default=nw=1:nk=1", str(mp3)], capture_output=True, text=True, check=True)
        return int(float(r.stdout.strip()))
    except Exception:
        return 0
