---
name: voice-session
description: Use when Mini-Jarvis must handle one spoken interaction after the wake word, including recording, silence cutoff, transcription, retries, and short user feedback.
---

# Voice Session

Use this skill after `hey mini-jarvis` is detected.

## Flow

1. Start recording immediately after the wake word.
2. Keep recording while VAD detects speech.
3. Stop after configured silence, default 1000 ms.
4. Save the utterance as WAV for STT and debugging.
5. Transcribe the WAV.
6. If transcription is empty, ask the user to repeat.
7. Send clean text to Hermes.
8. Return the Hermes response to TTS or console.

## Rules

- Do not send the wake word itself to Hermes.
- Prefer short confirmations only when something fails.
- Cap recording duration with `max_record_seconds`.
- If the microphone fails, report the device/config problem instead of retrying forever.
- If STT confidence is unavailable, treat empty or very short text as a retry case.
