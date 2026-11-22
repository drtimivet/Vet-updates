"""Synthèse vocale (Microsoft Edge TTS, gratuit) et assemblage MP3 avec ffmpeg.

Robustesse : texte nettoyé avant envoi, nouvelles tentatives espacées, découpage
en phrases si un passage est refusé, et un passage impossible à lire est sauté
plutôt que de bloquer tout l'épisode."""
from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import time
from pathlib import Path

MAX_FAILED_RATIO = 0.25   # au-delà, le service est jugé indisponible : l'épisode échoue


async def _tts(text: str, voice: str, rate: str, path: Path):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def clean_text(text: str) -> str:
    """Retire ce qui peut faire échouer la synthèse : balises, markdown, caractères de contrôle."""
    t = re.sub(r"<[^>]+>", " ", text)
    t = t.replace("&", " et ").replace("*", "").replace("#", "").replace("_", " ")
    t = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _speakable(text: str) -> bool:
    return bool(re.search(r"[A-Za-zÀ-ÿ0-9]", text))


def _try_tts(text: str, voice: str, rate: str, path: Path, attempts: int = 4) -> bool:
    for i in range(attempts):
        try:
            asyncio.run(_tts(text, voice, rate, path))
            if path.exists() and path.stat().st_size > 0:
                return True
        except Exception as e:
            print(f"    tentative {i + 1}/{attempts} refusée ({type(e).__name__})")
        time.sleep([2, 5, 10, 20][min(i, 3)])
    return False


def _synthesize_segment(text: str, voice: str, rate: str, base: Path) -> list[Path]:
    """Renvoie les fichiers audio d'un passage ; liste vide si impossible."""
    p = base.with_suffix(".mp3")
    if _try_tts(text, voice, rate, p):
        return [p]
    # Plan B : phrase par phrase, en sautant les phrases refusées.
    out = []
    for j, sent in enumerate(s for s in re.split(r"(?<=[.!?…])\s+", text) if _speakable(s)):
        q = base.with_name(f"{base.name}-{j:02d}.mp3")
        if _try_tts(sent, voice, rate, q, attempts=2):
            out.append(q)
        else:
            print(f"    phrase sautée : {sent[:80]}")
    return out


def synthesize(segments: list[dict], voices: list[str], rate: str, out_mp3: Path, work: Path) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg est requis pour assembler l'épisode (https://ffmpeg.org).")
    parts_dir = work / "parts"
    shutil.rmtree(parts_dir, ignore_errors=True)
    parts_dir.mkdir(parents=True, exist_ok=True)
    silence = parts_dir / "silence.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono", "-t", "0.6", "-c:a", "libmp3lame", "-b:a", "48k",
                    str(silence)], check=True)
    files, failed, total = [], 0, 0
    for i, seg in enumerate(segments):
        text = clean_text(seg.get("text", ""))
        if not _speakable(text):
            continue
        total += 1
        voice = voices[seg.get("speaker", 0) % len(voices)]
        got = _synthesize_segment(text, voice, rate, parts_dir / f"{i:04d}")
        if not got:
            failed += 1
            print(f"  ! passage {i} sauté (synthèse vocale refusée) : {text[:80]}")
            if failed >= 4 and failed > MAX_FAILED_RATIO * total:   # panne générale : on arrête vite
                raise RuntimeError(f"Synthèse vocale indisponible : {failed}/{total} passages refusés. "
                                   "Relancez plus tard.")
        for f in got:
            files += [f, silence]
        time.sleep(0.3)   # ménage le service gratuit
    if not files or failed > MAX_FAILED_RATIO * max(total, 1):
        raise RuntimeError(f"Synthèse vocale indisponible : {failed}/{total} passages refusés. "
                           "Relancez plus tard ou mettez à jour edge-tts.")
    if failed:
        print(f"  ! {failed} passage(s) sur {total} sauté(s) — épisode publié malgré tout")
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
