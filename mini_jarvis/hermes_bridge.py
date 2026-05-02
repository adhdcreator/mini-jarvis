from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol

import requests

from .config import HermesConfig


class HermesBridgeError(RuntimeError):
    """Raised when Mini-Jarvis cannot send to or read from Hermes."""


@dataclass(slots=True)
class HermesResponse:
    text: str
    raw: Any = None


class HermesBridge(Protocol):
    def ask(self, message: str) -> HermesResponse:
        """Send a message to Hermes and return its text response."""


class APIHermesBridge:
    def __init__(self, config: HermesConfig) -> None:
        self._endpoint = config.endpoint
        self._timeout = config.timeout_seconds

    def ask(self, message: str) -> HermesResponse:
        try:
            response = requests.post(
                self._endpoint,
                json={"message": message},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise HermesBridgeError(f"No pude hablar con Hermes por API: {exc}") from exc

        try:
            payload = response.json()
        except json.JSONDecodeError:
            text = response.text.strip()
            if not text:
                raise HermesBridgeError("Hermes respondio vacio")
            return HermesResponse(text=text, raw=response.text)

        text = extract_hermes_text(payload)
        return HermesResponse(text=text, raw=payload)


class CLIHermesBridge:
    def __init__(self, config: HermesConfig) -> None:
        if not config.command.strip():
            raise HermesBridgeError("hermes.command esta vacio")
        self._command = shlex.split(config.command)
        self._timeout = config.timeout_seconds

    def ask(self, message: str) -> HermesResponse:
        try:
            completed = subprocess.run(
                self._command,
                input=message,
                text=True,
                capture_output=True,
                timeout=self._timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise HermesBridgeError(f"No pude ejecutar Hermes CLI: {exc}") from exc

        if completed.returncode != 0:
            raise HermesBridgeError(completed.stderr.strip() or "Hermes CLI fallo")

        text = completed.stdout.strip()
        if not text:
            raise HermesBridgeError("Hermes CLI no devolvio respuesta")
        return HermesResponse(text=text, raw=completed.stdout)


class EchoHermesBridge:
    """Development bridge that proves the Mini-Jarvis pipeline without Hermes."""

    def ask(self, message: str) -> HermesResponse:
        return HermesResponse(text=f"Hermes echo: {message}", raw={"echo": message})


def build_hermes_bridge(config: HermesConfig) -> HermesBridge:
    mode = config.mode.lower()
    if mode == "api":
        return APIHermesBridge(config)
    if mode == "cli":
        return CLIHermesBridge(config)
    if mode == "echo":
        return EchoHermesBridge()
    raise ValueError(f"Modo Hermes no soportado: {config.mode}")


def extract_hermes_text(payload: Any) -> str:
    if isinstance(payload, str):
        text = payload.strip()
        if text:
            return text

    if isinstance(payload, dict):
        for key in ("response", "answer", "text", "message", "content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
                text = first.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()

    raise HermesBridgeError("No pude extraer texto de la respuesta de Hermes")
