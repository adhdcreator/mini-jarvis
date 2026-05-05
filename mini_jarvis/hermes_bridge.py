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
    tool_calls: tuple["HermesToolCall", ...] = ()


@dataclass(frozen=True, slots=True)
class HermesToolCall:
    name: str
    arguments: Any
    id: str | None = None


def format_hermes_tool_calls(tool_calls: tuple[HermesToolCall, ...]) -> str:
    lines: list[str] = []
    for index, call in enumerate(tool_calls, start=1):
        label = f"{index}. {call.name}"
        if call.id:
            label = f"{label} ({call.id})"
        lines.append(f"{label}: {_format_tool_arguments(call.arguments)}")
    return "\n".join(lines)


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

        return build_hermes_response(payload)


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

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return HermesResponse(text=text, raw=completed.stdout)

        return build_hermes_response(payload)


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


def build_hermes_response(payload: Any) -> HermesResponse:
    tool_calls = extract_hermes_tool_calls(payload)
    try:
        text = extract_hermes_text(payload)
    except HermesBridgeError:
        if not tool_calls:
            raise
        text = ""
    return HermesResponse(text=text, raw=payload, tool_calls=tool_calls)


def extract_hermes_text(payload: Any) -> str:
    if isinstance(payload, str):
        text = payload.strip()
        if text:
            return text

    if isinstance(payload, dict):
        for key in ("response", "answer", "text", "message", "content", "output_text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        content_text = _extract_text_from_content(payload.get("content"))
        if content_text:
            return content_text

        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    content_text = _extract_text_from_content(message.get("content"))
                    if content_text:
                        return content_text
                text = first.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()

        output = payload.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                for key in ("text", "output_text"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                content_text = _extract_text_from_content(item.get("content"))
                if content_text:
                    return content_text

    raise HermesBridgeError("No pude extraer texto de la respuesta de Hermes")


def extract_hermes_tool_calls(payload: Any) -> tuple[HermesToolCall, ...]:
    calls: list[HermesToolCall] = []
    for candidate in _iter_tool_call_containers(payload):
        if isinstance(candidate, list):
            calls.extend(_parse_tool_call(item) for item in candidate)
        elif isinstance(candidate, dict):
            calls.append(_parse_tool_call(candidate))
    return tuple(call for call in calls if call.name)


def _iter_tool_call_containers(payload: Any) -> list[Any]:
    if not isinstance(payload, dict):
        return []

    containers: list[Any] = []
    for key in ("tool_calls", "toolCalls", "function_call", "functionCall", "output", "content"):
        value = payload.get(key)
        if value:
            containers.append(value)

    message = payload.get("message")
    if isinstance(message, dict):
        containers.extend(_iter_tool_call_containers(message))

    choices = payload.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            containers.extend(_iter_tool_call_containers(choice))

    return containers


def _extract_text_from_content(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if not isinstance(item, dict):
                continue
            for key in ("text", "output_text"):
                text = item.get(key)
                if isinstance(text, str) and text.strip():
                    return text.strip()
    return ""


def _parse_tool_call(value: Any) -> HermesToolCall:
    if not isinstance(value, dict):
        return HermesToolCall(name="", arguments=None)

    call_id = _string_or_none(value.get("id") or value.get("call_id") or value.get("tool_call_id"))
    function = value.get("function")
    if isinstance(function, dict):
        return HermesToolCall(
            id=call_id,
            name=str(function.get("name") or ""),
            arguments=_parse_tool_arguments(function.get("arguments")),
        )

    name = value.get("name") or value.get("tool_name") or value.get("function_name")
    arguments = value.get("arguments", value.get("args", value.get("input")))
    return HermesToolCall(
        id=call_id,
        name=str(name or ""),
        arguments=_parse_tool_arguments(arguments),
    )


def _parse_tool_arguments(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return {}
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value
    if value is None:
        return {}
    return value


def _format_tool_arguments(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
