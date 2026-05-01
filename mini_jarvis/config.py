from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class WakeWordConfig:
    provider: str = "openwakeword"
    phrase: str = "hey mini-jarvis"
    threshold: float = 0.50
    model_paths: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_ms: int = 80
    silence_timeout_ms: int = 1000
    max_record_seconds: int = 20


@dataclass(slots=True)
class VADConfig:
    provider: str = "energy"
    energy_threshold: int = 500
    webrtc_aggressiveness: int = 2


@dataclass(slots=True)
class STTConfig:
    provider: str = "whisper"
    model: str = "base"
    language: str | None = "es"


@dataclass(slots=True)
class HermesConfig:
    mode: str = "api"
    endpoint: str = "http://localhost:8000/message"
    timeout_seconds: int = 60
    command: str = ""
    require_open: bool = True


@dataclass(slots=True)
class TTSConfig:
    enabled: bool = True
    provider: str = "minimax"
    max_chars: int = 1200
    daily_limit_chars: int | None = None
    play_audio: bool = True
    save_audio: bool = True


@dataclass(slots=True)
class MiniMaxConfig:
    api_host: str = "https://api.minimax.io"
    api_key: str = ""
    model: str = "speech-2.8-turbo"
    voice_id: str = "Spanish_Trustworthy_Man"
    language_boost: str = "Spanish"
    format: str = "mp3"
    sample_rate: int = 32000
    bitrate: int = 128000
    channel: int = 1
    speed: float = 1.0
    volume: float = 1.0
    pitch: int = 0
    output_format: str = "hex"


@dataclass(slots=True)
class PathsConfig:
    audio_dir: Path = Path("artifacts/audio")
    usage_file: Path = Path("artifacts/minimax_usage.json")


@dataclass(slots=True)
class AppConfig:
    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    hermes: HermesConfig = field(default_factory=HermesConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    minimax: MiniMaxConfig = field(default_factory=MiniMaxConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load config from TOML and apply environment overrides."""
    config_path = Path(path or "config.toml")
    data: dict[str, Any] = {}

    if config_path.exists():
        with config_path.open("rb") as fh:
            data = tomllib.load(fh)

    cfg = AppConfig(
        wake_word=_build(WakeWordConfig, data.get("wake_word", {})),
        audio=_build(AudioConfig, data.get("audio", {})),
        vad=_build(VADConfig, data.get("vad", {})),
        stt=_build(STTConfig, data.get("stt", {})),
        hermes=_build(HermesConfig, data.get("hermes", {})),
        tts=_build(TTSConfig, data.get("tts", {})),
        minimax=_build(MiniMaxConfig, data.get("minimax", {})),
        paths=_build_paths(data.get("paths", {})),
    )
    _apply_env_overrides(cfg)
    return cfg


def _build(cls: type[Any], values: dict[str, Any]) -> Any:
    allowed = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
    return cls(**{key: value for key, value in values.items() if key in allowed})


def _build_paths(values: dict[str, Any]) -> PathsConfig:
    return PathsConfig(
        audio_dir=Path(values.get("audio_dir", "artifacts/audio")),
        usage_file=Path(values.get("usage_file", "artifacts/minimax_usage.json")),
    )


def _apply_env_overrides(cfg: AppConfig) -> None:
    cfg.minimax.api_key = os.getenv("MINIMAX_API_KEY", cfg.minimax.api_key)
    cfg.minimax.api_host = os.getenv("MINIMAX_API_HOST", cfg.minimax.api_host)
    cfg.hermes.endpoint = os.getenv("HERMES_ENDPOINT", cfg.hermes.endpoint)
    cfg.hermes.command = os.getenv("HERMES_COMMAND", cfg.hermes.command)


def ensure_runtime_dirs(cfg: AppConfig) -> None:
    cfg.paths.audio_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.usage_file.parent.mkdir(parents=True, exist_ok=True)


def write_example_config(path: str | Path = "config.toml") -> Path:
    source = Path(__file__).resolve().parent.parent / "config.example.toml"
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"{target} already exists")
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return target
