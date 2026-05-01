from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mini_jarvis.config import load_config
from mini_jarvis.hermes_bridge import extract_hermes_text
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


class HermesBridgeTests(unittest.TestCase):
    def test_extract_simple_response(self) -> None:
        self.assertEqual(extract_hermes_text({"response": " listo "}), "listo")

    def test_extract_openai_style_response(self) -> None:
        payload = {"choices": [{"message": {"content": "hola"}}]}
        self.assertEqual(extract_hermes_text(payload), "hola")


class TTSTests(unittest.TestCase):
    def test_limit_text(self) -> None:
        self.assertEqual(_limit_text("abcdef", 4), "a...")
        self.assertEqual(_limit_text("abcdef", 2), "ab")


if __name__ == "__main__":
    unittest.main()
