# Mini-Jarvis

Mini-Jarvis es una capa de voz para Hermes Agent.

Cuando Hermes esté abierto, Mini-Jarvis permite decir `hey mini-jarvis`, grabar
la petición, enviarla a Hermes y reproducir la respuesta con voz.

```text
Mini-Jarvis = wake word + audio + STT + bridge + TTS
Hermes      = razonamiento + herramientas + respuesta final
```

## Flujo

```text
Micrófono
  -> wake_word.py detecta "hey mini-jarvis"
  -> audio.py graba la petición
  -> vad.py corta al detectar silencio
  -> stt.py convierte audio a texto
  -> hermes_bridge.py envía texto a Hermes
  -> Hermes devuelve texto
  -> tts.py envía texto a MiniMax
  -> player.py reproduce el audio
```

## Estado actual

Ya existe la base del proyecto:

```text
mini_jarvis/
  main.py
  config.py
  audio.py
  wake_word.py
  vad.py
  stt.py
  hermes_bridge.py
  tts.py
  tts_minimax.py
  player.py
  session.py
skills/
  voice-session/SKILL.md
  hermes-bridge/SKILL.md
  minimax-tts/SKILL.md
config.example.toml
pyproject.toml
```

## Requisitos

- Python 3.11 o superior.
- Hermes Agent disponible por API o CLI, salvo que uses `mode = "echo"`.
- Para sesiones de voz: micrófono, salida de audio y dependencias opcionales.
- Para MiniMax TTS: una clave en `MINIMAX_API_KEY`.

## Instalar

Instalación mínima, suficiente para probar configuración, Hermes en modo `echo`
y comandos sin micrófono:

```bash
python -m pip install -e .
```

Instalación completa para el flujo local de voz:

```bash
python -m pip install -e ".[all]"
```

Dependencias de desarrollo y tests:

```bash
python -m pip install -e ".[dev]"
```

## Arranque rápido

Crear la configuración local:

```bash
mini-jarvis init
```

O usar el ejemplo:

```bash
cp config.example.toml config.toml
```

Variables necesarias para MiniMax:

```bash
export MINIMAX_API_KEY="tu_api_key"
export MINIMAX_API_HOST="https://api.minimax.io"
```

Revisar dependencias y configuración:

```bash
mini-jarvis doctor
```

Probar sin Hermes real:

```toml
[hermes]
mode = "echo"

[tts]
enabled = false
```

Luego:

```bash
mini-jarvis ask "hola hermes"
```

## Comandos

| Comando | Uso |
| --- | --- |
| `mini-jarvis init` | Crea `config.toml` desde `config.example.toml`. |
| `mini-jarvis doctor` | Valida configuración, dependencias opcionales y variables de entorno. |
| `mini-jarvis ask "texto"` | Envía texto a Hermes y muestra la respuesta. |
| `mini-jarvis ask "texto" --speak` | Envía texto a Hermes y reproduce la respuesta con TTS. |
| `mini-jarvis speak "texto"` | Genera audio con el proveedor TTS configurado. |
| `mini-jarvis run` | Espera el wake word, graba, transcribe, consulta Hermes y responde por voz. |
| `mini-jarvis run --loop` | Repite sesiones de voz hasta interrumpir el proceso. |

## Probar flujos

Probar MiniMax TTS:

```bash
mini-jarvis speak "Hola, soy Mini-Jarvis."
```

Probar con Hermes por API:

```toml
[hermes]
mode = "api"
endpoint = "http://localhost:8000/message"
```

Luego:

```bash
mini-jarvis ask "resumime lo que tengo abierto" --speak
```

Ejecutar una sesión de voz completa:

```bash
mini-jarvis run
```

Escuchar en loop:

```bash
mini-jarvis run --loop
```

Ejecutar tests:

```bash
pytest
```

## Subir a GitHub

El repositorio incluye `.gitignore` para no subir configuración local, audios
generados ni archivos de entorno. Si todavía no tiene remoto configurado:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin git@github.com:TU_USUARIO/mini-jarvis.git
git push -u origin main
```

Si ya existe un remoto:

```bash
git status --short
git add README.md
git commit -m "Improve README"
git push
```

Cada push a `main` y cada pull request hacia `main` ejecutan los tests con
GitHub Actions.

## Config principal

```toml
[wake_word]
provider = "openwakeword"
phrase = "hey mini-jarvis"
threshold = 0.50

[audio]
sample_rate = 16000
channels = 1
chunk_ms = 80
silence_timeout_ms = 1000
max_record_seconds = 20

[vad]
provider = "energy"
energy_threshold = 500

[stt]
provider = "whisper"
model = "base"
language = "es"

[hermes]
mode = "api"
endpoint = "http://localhost:8000/message"
timeout_seconds = 60
command = ""
require_open = true

[tts]
enabled = true
provider = "minimax"
max_chars = 1200
daily_limit_chars = 4000
play_audio = true
save_audio = true

[minimax]
api_host = "https://api.minimax.io"
model = "speech-2.8-turbo"
voice_id = "Spanish_Trustworthy_Man"
language_boost = "Spanish"
format = "mp3"
output_format = "hex"

[paths]
audio_dir = "artifacts/audio"
usage_file = "artifacts/minimax_usage.json"
```

## Hermes Bridge

Mini-Jarvis soporta tres modos:

```text
api  -> POST al endpoint configurado
cli  -> ejecuta un comando local y manda el texto por stdin
echo -> modo de prueba sin Hermes
```

La respuesta de Hermes puede venir como texto plano o JSON. El bridge intenta
leer campos comunes como:

```text
response, answer, text, message, content, choices[0].message.content
```

Si Hermes devuelve tool calls estructurados, Mini-Jarvis los conserva en
`HermesResponse.tool_calls` para que una integración superior pueda auditarlos o
mostrarlos sin perder el texto final. Soporta formatos comunes:

```text
tool_calls, toolCalls, function_call, functionCall,
choices[0].message.tool_calls
```

En modo `cli`, si stdout es JSON, se procesa igual que la respuesta de API. Si
stdout es texto plano, se mantiene como respuesta final.

## MiniMax TTS

MiniMax se usa solo al final:

```text
respuesta de Hermes -> MiniMax T2A -> MP3 -> player.py
```

El cliente usa la API HTTP T2A v2:

```text
POST https://api.minimax.io/v1/t2a_v2
```

Por defecto pide audio en `hex`, lo decodifica, lo guarda en
`artifacts/audio/` y lo reproduce si hay un player disponible.

## Skills

Los skills son cortos y accionables:

- `voice-session`: reglas de grabación, silencio, retry y STT.
- `hermes-bridge`: cómo enviar mensajes a Hermes y extraer respuestas.
- `minimax-tts`: cómo generar voz y controlar caracteres.

## Pendientes reales

- Confirmar el endpoint o CLI exacto de Hermes.
- Elegir una voz real de MiniMax para `voice_id`.
- Entrenar o seleccionar modelo de `openwakeword` para `hey mini-jarvis`.
- Ajustar `energy_threshold` o cambiar a WebRTC/Silero VAD.
- Probar latencia con micrófono real.
- Decidir si el proceso correrá como servicio en background.
