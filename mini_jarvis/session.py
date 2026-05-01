from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .audio import iter_microphone_chunks, record_until_silence, save_wav
from .config import AppConfig, ensure_runtime_dirs
from .hermes_bridge import HermesResponse, build_hermes_bridge
from .stt import Transcript, build_transcriber
from .tts import build_tts_provider
from .vad import build_vad
from .wake_word import WakeWordEvent, build_wake_word_detector, wait_for_wake_word


@dataclass(slots=True)
class VoiceRunResult:
    wake: WakeWordEvent
    audio_path: Path
    transcript: Transcript
    hermes: HermesResponse
    spoken_audio_path: Path | None


def run_voice_once(config: AppConfig) -> VoiceRunResult:
    ensure_runtime_dirs(config)

    detector = build_wake_word_detector(config.wake_word)
    wake_chunks = iter_microphone_chunks(config.audio)
    try:
        wake = wait_for_wake_word(wake_chunks, detector)
    finally:
        _close_iterator(wake_chunks)

    vad = build_vad(config.vad, config.audio)
    record_chunks = iter_microphone_chunks(config.audio)
    try:
        recording = record_until_silence(
            record_chunks,
            detector=vad,
            config=config.audio,
        )
    finally:
        _close_iterator(record_chunks)
    audio_path = save_wav(recording, config.paths.audio_dir / "last-input.wav")

    transcriber = build_transcriber(config.stt)
    transcript = transcriber.transcribe_file(audio_path)

    hermes = build_hermes_bridge(config.hermes).ask(transcript.text)
    spoken_audio_path = build_tts_provider(config).speak(hermes.text)

    return VoiceRunResult(
        wake=wake,
        audio_path=audio_path,
        transcript=transcript,
        hermes=hermes,
        spoken_audio_path=spoken_audio_path,
    )


def ask_text(config: AppConfig, message: str, *, speak: bool = False) -> HermesResponse:
    ensure_runtime_dirs(config)
    response = build_hermes_bridge(config.hermes).ask(message)
    print(response.text)
    if speak:
        build_tts_provider(config).speak(response.text)
    return response


def _close_iterator(iterator: object) -> None:
    close = getattr(iterator, "close", None)
    if callable(close):
        close()
