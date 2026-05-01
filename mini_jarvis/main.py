from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

from .config import ensure_runtime_dirs, load_config, write_example_config
from .hermes_bridge import build_hermes_bridge
from .session import ask_text, run_voice_once
from .tts import build_tts_provider


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print("\nMini-Jarvis detenido.")
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mini-jarvis")
    parser.add_argument(
        "-c",
        "--config",
        default="config.toml",
        help="Ruta al archivo TOML de configuracion.",
    )
    sub = parser.add_subparsers(required=True)

    doctor = sub.add_parser("doctor", help="Revisa configuracion y dependencias.")
    doctor.set_defaults(func=cmd_doctor)

    init = sub.add_parser("init", help="Crea config.toml desde config.example.toml.")
    init.add_argument("--force", action="store_true", help="Sobrescribe config.toml.")
    init.set_defaults(func=cmd_init)

    ask = sub.add_parser("ask", help="Envia texto a Hermes.")
    ask.add_argument("message", nargs="+")
    ask.add_argument("--speak", action="store_true", help="Lee la respuesta con TTS.")
    ask.set_defaults(func=cmd_ask)

    speak = sub.add_parser("speak", help="Genera voz para un texto.")
    speak.add_argument("text", nargs="+")
    speak.set_defaults(func=cmd_speak)

    run = sub.add_parser("run", help="Ejecuta una sesion completa por voz.")
    run.add_argument("--loop", action="store_true", help="Vuelve a escuchar al terminar.")
    run.set_defaults(func=cmd_run)

    return parser


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.config)
    if target.exists() and args.force:
        target.unlink()
    created = write_example_config(target)
    print(f"Config creada en {created}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    ensure_runtime_dirs(cfg)

    print("Mini-Jarvis doctor")
    print(f"Config: {Path(args.config).resolve()}")
    print(f"Hermes mode: {cfg.hermes.mode}")
    print(f"TTS: {cfg.tts.provider if cfg.tts.enabled else 'disabled'}")
    print(f"Audio dir: {cfg.paths.audio_dir}")
    print("")
    print("Dependencias opcionales:")
    for name, module in {
        "sounddevice": "sounddevice",
        "numpy": "numpy",
        "openwakeword": "openwakeword",
        "webrtcvad": "webrtcvad",
        "whisper": "whisper",
    }.items():
        print(f"- {name}: {'ok' if _has_module(module) else 'missing'}")

    print("")
    print("Variables:")
    print(f"- MINIMAX_API_KEY: {'ok' if os.getenv('MINIMAX_API_KEY') else 'missing'}")
    print(f"- HERMES_ENDPOINT: {os.getenv('HERMES_ENDPOINT') or cfg.hermes.endpoint}")

    if cfg.hermes.mode == "echo":
        response = build_hermes_bridge(cfg.hermes).ask("doctor")
        print(f"Hermes echo: {response.text}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    message = " ".join(args.message)
    ask_text(cfg, message, speak=args.speak)
    return 0


def cmd_speak(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    text = " ".join(args.text)
    path = build_tts_provider(cfg).speak(text)
    if path:
        print(f"Audio: {path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    while True:
        result = run_voice_once(cfg)
        print(f"Wake word: {result.wake.label} ({result.wake.score:.2f})")
        print(f"Audio: {result.audio_path}")
        print(f"Usuario: {result.transcript.text}")
        print(f"Hermes: {result.hermes.text}")
        if not args.loop:
            return 0


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


if __name__ == "__main__":
    raise SystemExit(main())
