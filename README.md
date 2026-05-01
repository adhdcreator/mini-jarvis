# Mini-Jarvis

Mini-Jarvis es una capa de voz para Hermes Agent.

Cuando Hermes este abierto, Mini-Jarvis permite decir `hey mini-jarvis`, grabar
la peticion, enviarla a Hermes y reproducir la respuesta con voz.

```text
Mini-Jarvis = wake word + audio + STT + bridge + TTS
Hermes      = razonamiento + herramientas + respuesta final
```

## Flujo

```text
Microfono
  -> wake_word.py detecta "hey mini-jarvis"
  -> audio.py graba la peticion
  -> vad.py corta al detectar silencio
  -> stt.py convierte audio a texto
  -> hermes_bridge.py envia texto a Hermes
  -> Hermes devuelve texto
  -> tts.py envia texto a MiniMax
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

## Instalar

Base:

```bash
python -m pip install -e .
```

Todo el flujo de voz local:

```bash
python -m pip install -e ".[all]"
```

Si solo quieres probar sin microfono:

```bash
python -m pip install -e .
```

## Configurar

Crear config:

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

## Probar

Revisar dependencias y configuracion:

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

Ejecutar una sesion de voz completa:

```bash
mini-jarvis run
```

Escuchar en loop:

```bash
mini-jarvis run --loop
```

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

- `voice-session`: reglas de grabacion, silencio, retry y STT.
- `hermes-bridge`: como enviar mensajes a Hermes y extraer respuestas.
- `minimax-tts`: como generar voz y controlar caracteres.

## Pendientes reales

- Confirmar el endpoint o CLI exacto de Hermes.
- Elegir una voz real de MiniMax para `voice_id`.
- Entrenar o seleccionar modelo de `openwakeword` para `hey mini-jarvis`.
- Ajustar `energy_threshold` o cambiar a WebRTC/Silero VAD.
- Probar latencia con microfono real.
- Decidir si el proceso correra como servicio en background.
