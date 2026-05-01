from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def play_audio_file(path: str | Path) -> bool:
    audio_path = Path(path)
    suffix = audio_path.suffix.lower()

    command = _find_player(suffix)
    if command is None:
        return False

    subprocess.run([*command, str(audio_path)], check=False)
    return True


def _find_player(suffix: str) -> list[str] | None:
    if sys.platform == "darwin" and shutil.which("afplay"):
        return ["afplay"]

    if suffix == ".mp3":
        for candidate in ("ffplay", "mpg123", "mpv"):
            if shutil.which(candidate):
                if candidate == "ffplay":
                    return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
                return [candidate]

    if suffix in {".wav", ".flac"}:
        for candidate in ("aplay", "paplay", "ffplay", "mpv"):
            if shutil.which(candidate):
                if candidate == "ffplay":
                    return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
                return [candidate]

    return None
