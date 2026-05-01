from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from .config import MiniMaxConfig


class MiniMaxTTSError(RuntimeError):
    """Raised when MiniMax cannot generate audio."""


@dataclass(slots=True)
class MiniMaxAudio:
    audio: bytes
    audio_format: str
    trace_id: str | None = None
    usage_characters: int = 0

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(self.audio)
        return output


class MiniMaxTTSClient:
    """HTTP client for MiniMax T2A v2.

    Official docs: https://platform.minimax.io/docs/api-reference/speech-t2a-http
    """

    def __init__(self, config: MiniMaxConfig) -> None:
        if not config.api_key:
            raise MiniMaxTTSError("Falta MINIMAX_API_KEY")
        self._config = config

    def synthesize(self, text: str) -> MiniMaxAudio:
        text = text.strip()
        if not text:
            raise MiniMaxTTSError("No hay texto para generar voz")

        payload = {
            "model": self._config.model,
            "text": text,
            "stream": False,
            "language_boost": self._config.language_boost,
            "output_format": self._config.output_format,
            "voice_setting": {
                "voice_id": self._config.voice_id,
                "speed": self._config.speed,
                "vol": self._config.volume,
                "pitch": self._config.pitch,
            },
            "audio_setting": {
                "sample_rate": self._config.sample_rate,
                "bitrate": self._config.bitrate,
                "format": self._config.format,
                "channel": self._config.channel,
            },
        }

        try:
            response = requests.post(
                self._endpoint,
                headers={
                    "Authorization": f"Bearer {self._config.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MiniMaxTTSError(f"MiniMax TTS fallo: {exc}") from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise MiniMaxTTSError("MiniMax no devolvio JSON valido") from exc
        base_resp = body.get("base_resp") or {}
        if base_resp.get("status_code", 0) != 0:
            message = base_resp.get("status_msg") or "MiniMax devolvio error"
            raise MiniMaxTTSError(str(message))

        data = body.get("data") or {}
        audio_value = data.get("audio")
        if not audio_value:
            raise MiniMaxTTSError("MiniMax no devolvio audio")

        audio_bytes = self._decode_audio(str(audio_value))
        extra = body.get("extra_info") or {}
        return MiniMaxAudio(
            audio=audio_bytes,
            audio_format=str(extra.get("audio_format") or self._config.format),
            trace_id=body.get("trace_id"),
            usage_characters=int(extra.get("usage_characters") or len(text)),
        )

    @property
    def _endpoint(self) -> str:
        host = self._config.api_host.rstrip("/")
        if host.endswith("/v1/t2a_v2"):
            return host
        return f"{host}/v1/t2a_v2"

    def _decode_audio(self, value: str) -> bytes:
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"}:
            response = requests.get(value, timeout=90)
            response.raise_for_status()
            return response.content
        try:
            return bytes.fromhex(value)
        except ValueError as exc:
            raise MiniMaxTTSError("El audio de MiniMax no es hex ni URL valida") from exc
