from __future__ import annotations

import array
import math
import sys
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .config import AudioConfig, VADConfig


@runtime_checkable
class VoiceActivityDetector(Protocol):
    def is_speech(self, pcm: bytes, sample_rate: int) -> bool:
        """Return True when the PCM chunk contains voice."""


@dataclass(slots=True)
class EnergyVAD:
    """Small dependency-free VAD for MVP/dev use."""

    threshold: int = 500

    def is_speech(self, pcm: bytes, sample_rate: int) -> bool:
        del sample_rate
        return _rms_int16(pcm) >= self.threshold


class WebRTCVAD:
    def __init__(self, aggressiveness: int = 2) -> None:
        try:
            import webrtcvad
        except ImportError as exc:
            raise RuntimeError(
                "Falta instalar WebRTC VAD: pip install 'mini-jarvis[vad]'"
            ) from exc

        self._vad = webrtcvad.Vad(aggressiveness)

    def is_speech(self, pcm: bytes, sample_rate: int) -> bool:
        return bool(self._vad.is_speech(pcm, sample_rate))


def build_vad(vad: VADConfig, audio: AudioConfig) -> VoiceActivityDetector:
    provider = vad.provider.lower()
    if provider == "energy":
        return EnergyVAD(threshold=vad.energy_threshold)
    if provider == "webrtc":
        _validate_webrtc_frame(audio)
        return WebRTCVAD(aggressiveness=vad.webrtc_aggressiveness)
    raise ValueError(f"Proveedor VAD no soportado: {vad.provider}")


def _validate_webrtc_frame(audio: AudioConfig) -> None:
    if audio.sample_rate not in {8000, 16000, 32000, 48000}:
        raise ValueError("WebRTC VAD requiere sample_rate 8000, 16000, 32000 o 48000")
    if audio.chunk_ms not in {10, 20, 30}:
        raise ValueError("WebRTC VAD requiere chunk_ms 10, 20 o 30")


def _rms_int16(pcm: bytes) -> float:
    if not pcm:
        return 0.0

    samples = array.array("h")
    samples.frombytes(pcm)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return 0.0

    square_sum = sum(sample * sample for sample in samples)
    return math.sqrt(square_sum / len(samples))
