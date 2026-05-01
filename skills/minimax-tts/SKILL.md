---
name: minimax-tts
description: Use when Mini-Jarvis must convert Hermes text responses into spoken audio with MiniMax Speech while controlling character usage and playback.
---

# MiniMax TTS

Use this skill after Hermes returns final text.

## Flow

1. Trim response to `tts.max_chars`.
2. Check daily character usage before calling MiniMax.
3. Call MiniMax T2A HTTP with `stream = false` for MVP.
4. Decode returned hex audio.
5. Save audio under `paths.audio_dir`.
6. Play audio when `tts.play_audio = true`.

## Defaults

- Model: `speech-2.8-turbo`
- Format: `mp3`
- Output format: `hex`
- Language boost: `Spanish`

## Rules

- Never call MiniMax with empty text.
- Keep spoken responses short to preserve daily quota.
- If `MINIMAX_API_KEY` is missing, fall back to console output or fail clearly.
- If no audio player is available, save the file and print its path.
