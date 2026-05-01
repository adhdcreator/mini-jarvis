from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from .config import AppConfig
from .player import play_audio_file
from .tts_minimax import MiniMaxTTSClient


class TTSError(RuntimeError):
    """Raised when text-to-speech fails."""


class TTSProvider(Protocol):
    def speak(self, text: str) -> Path | None:
        """Generate and optionally play audio for text."""


class ConsoleTTS:
    def speak(self, text: str) -> Path | None:
        print(text)
        return None


@dataclass(slots=True)
class DailyCharacterBudget:
    path: Path
    limit: int | None = None

    def can_spend(self, count: int) -> bool:
        if self.limit is None:
            return True
        usage = self._read()
        return usage["characters"] + count <= self.limit

    def spend(self, count: int) -> None:
        usage = self._read()
        usage["characters"] += count
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(usage, indent=2), encoding="utf-8")

    def _read(self) -> dict[str, int | str]:
        today = date.today().isoformat()
        if not self.path.exists():
            return {"date": today, "characters": 0}

        try:
            usage = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"date": today, "characters": 0}

        if usage.get("date") != today:
            return {"date": today, "characters": 0}
        return {"date": today, "characters": int(usage.get("characters", 0))}


class MiniMaxTTS:
    def __init__(self, config: AppConfig) -> None:
        self._cfg = config
        self._client = MiniMaxTTSClient(config.minimax)
        self._budget = DailyCharacterBudget(
            config.paths.usage_file,
            limit=config.tts.daily_limit_chars,
        )

    def speak(self, text: str) -> Path | None:
        text = _limit_text(text, self._cfg.tts.max_chars)
        if not self._budget.can_spend(len(text)):
            raise TTSError("Se alcanzo el limite diario configurado de caracteres TTS")

        audio = self._client.synthesize(text)
        self._budget.spend(audio.usage_characters)

        output_path: Path | None = None
        if self._cfg.tts.save_audio or self._cfg.tts.play_audio:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            filename = f"minimax-{stamp}.{audio.audio_format}"
            output_path = audio.save(self._cfg.paths.audio_dir / filename)

        if self._cfg.tts.play_audio and output_path is not None:
            played = play_audio_file(output_path)
            if not played:
                print(f"Audio guardado en {output_path}; no encontre reproductor compatible.")

        return output_path


def build_tts_provider(config: AppConfig) -> TTSProvider:
    if not config.tts.enabled:
        return ConsoleTTS()

    provider = config.tts.provider.lower()
    if provider == "minimax":
        return MiniMaxTTS(config)
    if provider == "console":
        return ConsoleTTS()
    raise ValueError(f"Proveedor TTS no soportado: {config.tts.provider}")


def _limit_text(text: str, max_chars: int) -> str:
    text = text.strip()
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3].rstrip() + "..."
