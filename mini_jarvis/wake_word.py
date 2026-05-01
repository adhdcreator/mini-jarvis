from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from .config import WakeWordConfig


class WakeWordError(RuntimeError):
    """Raised when the wake word provider cannot be used."""


@dataclass(slots=True)
class WakeWordEvent:
    label: str
    score: float


class WakeWordDetector(Protocol):
    def process(self, pcm: bytes) -> WakeWordEvent | None:
        """Return an event when the wake word is detected."""


class OpenWakeWordDetector:
    def __init__(self, config: WakeWordConfig) -> None:
        try:
            import numpy as np
            from openwakeword.model import Model
        except ImportError as exc:
            raise WakeWordError(
                "Falta instalar openwakeword: pip install 'mini-jarvis[wakeword]'"
            ) from exc

        kwargs: dict[str, object] = {}
        if config.model_paths:
            kwargs["wakeword_models"] = config.model_paths

        self._np = np
        self._model = Model(**kwargs)
        self._threshold = config.threshold
        self._labels = set(config.labels)
        self._phrase = config.phrase

    def process(self, pcm: bytes) -> WakeWordEvent | None:
        samples = self._np.frombuffer(pcm, dtype=self._np.int16)
        scores = self._model.predict(samples)
        if not scores:
            return None

        candidates = {
            label: float(score)
            for label, score in scores.items()
            if not self._labels or label in self._labels
        }
        if not candidates:
            return None

        label, score = max(candidates.items(), key=lambda item: item[1])
        if score >= self._threshold:
            return WakeWordEvent(label=label or self._phrase, score=score)
        return None


class KeyboardWakeWordDetector:
    """Development detector used by tests or manual CLI flows."""

    def __init__(self, label: str = "manual") -> None:
        self._label = label
        self._used = False

    def wait(self) -> WakeWordEvent:
        input("Presiona Enter para simular 'hey mini-jarvis'...")
        return WakeWordEvent(label=self._label, score=1.0)

    def process(self, pcm: bytes) -> WakeWordEvent | None:
        del pcm
        if self._used:
            return None
        self._used = True
        return WakeWordEvent(label=self._label, score=1.0)


def build_wake_word_detector(config: WakeWordConfig) -> WakeWordDetector:
    provider = config.provider.lower()
    if provider == "openwakeword":
        return OpenWakeWordDetector(config)
    if provider in {"keyboard", "manual"}:
        return KeyboardWakeWordDetector(config.phrase)
    raise ValueError(f"Proveedor de wake word no soportado: {config.provider}")


def wait_for_wake_word(
    chunks: Iterator[bytes],
    detector: WakeWordDetector,
) -> WakeWordEvent:
    for chunk in chunks:
        event = detector.process(chunk)
        if event is not None:
            return event
    raise WakeWordError("El stream de audio termino antes de detectar wake word")
