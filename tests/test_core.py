from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from mini_jarvis.audio import AudioError, record_until_silence
from mini_jarvis.config import AudioConfig, ConfigError, HermesConfig, MiniMaxConfig, load_config
from mini_jarvis.hermes_bridge import (
    CLIHermesBridge,
    HermesBridgeError,
    extract_hermes_text,
    extract_hermes_tool_calls,
)
from mini_jarvis.tts_minimax import MiniMaxTTSError, MiniMaxTTSClient
from mini_jarvis.tts import _limit_text


class ConfigTests(unittest.TestCase):
    def test_load_config_defaults_when_file_missing(self) -> None:
        cfg = load_config("missing-config.toml")
        self.assertEqual(cfg.wake_word.phrase, "hey mini-jarvis")
        self.assertEqual(cfg.hermes.mode, "api")

    def test_load_config_from_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
[hermes]
mode = "echo"

[tts]
enabled = false
""".strip(),
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(cfg.hermes.mode, "echo")
            self.assertFalse(cfg.tts.enabled)

    def test_load_config_rejects_unknown_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("[hermes]\nmod = 'echo'\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)

    def test_load_config_rejects_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text("[audio]\nchunk_ms = 0\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path)


class HermesBridgeTests(unittest.TestCase):
    def test_extract_simple_response(self) -> None:
        self.assertEqual(extract_hermes_text({"response": " listo "}), "listo")

    def test_extract_openai_style_response(self) -> None:
        payload = {"choices": [{"message": {"content": "hola"}}]}
        self.assertEqual(extract_hermes_text(payload), "hola")

    def test_extract_openai_style_tool_calls(self) -> None:
        payload = {
            "choices": [
                {
                    "message": {
                        "content": "voy a revisar eso",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "search_notes",
                                    "arguments": '{"query": "mini jarvis"}',
                                },
                            }
                        ],
                    }
                }
            ]
        }
        calls = extract_hermes_tool_calls(payload)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].id, "call_1")
        self.assertEqual(calls[0].name, "search_notes")
        self.assertEqual(calls[0].arguments, {"query": "mini jarvis"})

    def test_extract_direct_tool_calls(self) -> None:
        payload = {
            "response": "listo",
            "tool_calls": [{"name": "open_app", "arguments": {"app": "Hermes"}}],
        }
        calls = extract_hermes_tool_calls(payload)
        self.assertEqual(calls[0].name, "open_app")
        self.assertEqual(calls[0].arguments, {"app": "Hermes"})

    @patch("mini_jarvis.hermes_bridge.subprocess.run", side_effect=FileNotFoundError("missing"))
    def test_cli_bridge_wraps_os_errors(self, run: Mock) -> None:
        bridge = CLIHermesBridge(HermesConfig(mode="cli", command="missing-hermes"))
        with self.assertRaises(HermesBridgeError):
            bridge.ask("hola")
        run.assert_called_once()

    @patch("mini_jarvis.hermes_bridge.subprocess.run")
    def test_cli_bridge_parses_json_tool_calls(self, run: Mock) -> None:
        run.return_value = Mock(
            returncode=0,
            stdout='{"response":"listo","tool_calls":[{"name":"lookup","arguments":"{\\"id\\": 7}"}]}',
            stderr="",
        )
        bridge = CLIHermesBridge(HermesConfig(mode="cli", command="hermes ask"))
        response = bridge.ask("hola")
        self.assertEqual(response.text, "listo")
        self.assertEqual(response.tool_calls[0].name, "lookup")
        self.assertEqual(response.tool_calls[0].arguments, {"id": 7})


class TTSTests(unittest.TestCase):
    def test_limit_text(self) -> None:
        self.assertEqual(_limit_text("abcdef", 4), "a...")
        self.assertEqual(_limit_text("abcdef", 2), "ab")

    @patch("mini_jarvis.tts_minimax.requests.get", side_effect=requests.Timeout("timeout"))
    def test_minimax_wraps_audio_download_errors(self, get: Mock) -> None:
        client = MiniMaxTTSClient(MiniMaxConfig(api_key="token"))
        with self.assertRaises(MiniMaxTTSError):
            client._decode_audio("https://example.test/audio.mp3")
        get.assert_called_once()


class AudioTests(unittest.TestCase):
    def test_record_until_silence_fails_when_no_speech_detected(self) -> None:
        class SilentDetector:
            def is_speech(self, pcm: bytes, sample_rate: int) -> bool:
                return False

        detector = SilentDetector()
        chunks = iter([b"\x00\x00", b"\x00\x00"])
        with self.assertRaises(AudioError):
            record_until_silence(chunks, detector=detector, config=AudioConfig(chunk_ms=10))


if __name__ == "__main__":
    unittest.main()
