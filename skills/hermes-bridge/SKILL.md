---
name: hermes-bridge
description: Use when Mini-Jarvis must send user text to Hermes Agent and retrieve the response through API, CLI, WebSocket, or a fallback integration.
---

# Hermes Bridge

Use this skill when Mini-Jarvis has clean user text and needs Hermes to answer.

## Priority

1. Use Hermes local API if available.
2. Use Hermes CLI if API is unavailable.
3. Use WebSocket if Hermes exposes a session channel.
4. Use window automation only as a last resort.

## Request

Send only the user request, not wake word metadata or audio logs.

When TTS is enabled, ask Hermes for concise responses:

```text
Respond in Spanish in 700 to 1200 characters maximum when possible.
```

## Response

Extract response text from common fields:

- `response`
- `answer`
- `text`
- `message`
- `content`
- OpenAI-style `choices[0].message.content`

## Failure Handling

- If Hermes is closed, tell the user Hermes must be opened.
- If Hermes times out, return a short timeout message.
- If response text cannot be extracted, log the raw response and fail clearly.
