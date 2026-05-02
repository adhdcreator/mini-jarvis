from __future__ import annotations

import time
import wave
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .config import AudioConfig


class AudioError(RuntimeError):
    """Raised when recording or audio persistence fails."""


@dataclass(slots=True)
class RecordedAudio:
    pcm: bytes
    sample_rate: int
    channels: int
    sample_width: int = 2

    @property
    def duration_seconds(self) -> float:
        frame_count = len(self.pcm) / (self.channels * self.sample_width)
        return frame_count / self.sample_rate


def iter_microphone_chunks(config: AudioConfig) -> Iterator[bytes]:
    """Yield raw 16-bit PCM chunks from the default microphone.

    Requires the optional `audio` dependencies: sounddevice and numpy.
    """
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise AudioError(
            "Falta instalar dependencias de audio: pip install 'mini-jarvis[audio]'"
        ) from exc

    blocksize = int(config.sample_rate * config.chunk_ms / 1000)
    try:
        with sd.RawInputStream(
            samplerate=config.sample_rate,
            blocksize=blocksize,
            channels=config.channels,
            dtype="int16",
        ) as stream:
            while True:
                chunk, overflowed = stream.read(blocksize)
                if overflowed:
                    # Keep going: a dropped chunk is better than aborting a voice session.
                    continue
                yield bytes(chunk)
    except Exception as exc:  # pragma: no cover - hardware dependent
        raise AudioError(f"No pude abrir el microfono: {exc}") from exc


def record_until_silence(
    chunks: Iterator[bytes],
    *,
    detector: object,
    config: AudioConfig,
) -> RecordedAudio:
    """Collect chunks until VAD sees enough silence after speech starts."""
    from .vad import VoiceActivityDetector

    if not isinstance(detector, VoiceActivityDetector):
        raise TypeError("detector must implement VoiceActivityDetector")

    frames: list[bytes] = []
    silence_ms = 0
    total_ms = 0
    heard_speech = False
    started_at = time.monotonic()

    for chunk in chunks:
        frames.append(chunk)
        total_ms += config.chunk_ms

        if detector.is_speech(chunk, config.sample_rate):
            heard_speech = True
            silence_ms = 0
        elif heard_speech:
            silence_ms += config.chunk_ms

        if heard_speech and silence_ms >= config.silence_timeout_ms:
            break
        if time.monotonic() - started_at >= config.max_record_seconds:
            break

    if not heard_speech:
        raise AudioError("No se detecto voz en la grabacion")

    return RecordedAudio(
        pcm=b"".join(frames),
        sample_rate=config.sample_rate,
        channels=config.channels,
    )


def save_wav(recording: RecordedAudio, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(recording.channels)
        wav.setsampwidth(recording.sample_width)
        wav.setframerate(recording.sample_rate)
        wav.writeframes(recording.pcm)
    return output
