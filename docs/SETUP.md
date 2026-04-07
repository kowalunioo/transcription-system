# Setup

## Runtime requirements

- `python3`
- `curl`
- `ffmpeg`
- `yt-dlp`
- a Python venv for clean execution
- `GROQ_API_KEY` available in the runtime environment

## 1. Create a Python environment

From the repository root:

```bash
python3 -m venv .venv-transcribe
. .venv-transcribe/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt
```

If you prefer to install `yt-dlp` separately:

```bash
python -m pip install yt-dlp
```

## 2. Verify Groq API access

```bash
curl -i https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY"
```

You should get HTTP 200.

## 3. Run the CLI

```bash
export OPENCLAW_TRANSCRIBE_BACKEND=groq
export OPENCLAW_TRANSCRIBE_GROQ_MODEL=whisper-large-v3-turbo
export OPENCLAW_TRANSCRIBE_GROQ_TIER=free
export OPENCLAW_TRANSCRIBE_VENV="$PWD/.venv-transcribe"

./bin/transcribe-media ./sample.mp3 --timestamps --output-format json
```

## 4. Install the OpenClaw plugin

From a workspace containing this repo:

```bash
openclaw plugins install -l ./transcription-system/openclaw-transcribe-plugin
openclaw gateway restart
```

If the plugin needs an explicit runtime path, set:

```bash
export OPENCLAW_TRANSCRIBE_VENV="$PWD/.venv-transcribe"
```

## 5. Recommended env

```bash
export OPENCLAW_TRANSCRIBE_BACKEND=groq
export OPENCLAW_TRANSCRIBE_GROQ_MODEL=whisper-large-v3-turbo
export OPENCLAW_TRANSCRIBE_GROQ_TIER=free
```

Use `dev` if your Groq tier supports `100 MB` uploads.
