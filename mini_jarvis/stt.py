from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import STTConfig


class TranscriptionError(RuntimeError):
    """Raised when speech-to-text fails."""


@dataclass(slots=True)
class Transcript:
    text: str
    language: str | None = None


class Transcriber(Protocol):
    def transcribe_file(self, audio_path: str | Path) -> Transcript:
        """Return a transcript for an audio file."""


class WhisperTranscriber:
    def __init__(self, config: STTConfig) -> None:
        try:
            import whisper
        except ImportError as exc:
            raise TranscriptionError(
                "Falta instalar Whisper: pip install 'mini-jarvis[stt]'"
            ) from exc

        self._config = config
        self._model = whisper.load_model(config.model)

    def transcribe_file(self, audio_path: str | Path) -> Transcript:
        options = {}
        if self._config.language:
            options["language"] = self._config.language
        result = self._model.transcribe(str(audio_path), **options)
        return Transcript(
            text=str(result.get("text", "")).strip(),
            language=result.get("language"),
        )


class StaticTranscriber:
    def __init__(self, text: str) -> None:
        self._text = text

    def transcribe_file(self, audio_path: str | Path) -> Transcript:
        del audio_path
        return Transcript(text=self._text)


def build_transcriber(config: STTConfig) -> Transcriber:
    provider = config.provider.lower()
    if provider == "whisper":
        return WhisperTranscriber(config)
    if provider == "static":
        return StaticTranscriber("")
    raise ValueError(f"Proveedor STT no soportado: {config.provider}")
