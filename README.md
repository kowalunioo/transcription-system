# OpenClaw Transcription System

Local-first transcription stack for OpenClaw and standalone use.

It can run as:
- a CLI for local files and YouTube audio
- a reusable Groq-backed media pipeline with preprocessing and chunking
- an OpenClaw plugin wrapper (`openclaw-transcribe-plugin/`)

## What it does

- transcribes local audio/video with Groq Whisper via a native Python HTTP request
- downloads YouTube audio with `yt-dlp`
- preprocesses oversized media to mono 16 kHz FLAC when needed
- splits oversized media into overlapping chunks automatically
- writes reusable transcript artifacts (`txt`, `json`, `srt`)
- caches runs by input fingerprint + settings

## Repo layout

- `bin/` — stable shell entrypoints
- `src/` — Python implementation
- `docs/` — setup, usage, config, architecture, troubleshooting
- `openclaw-transcribe-plugin/` — plugin wrapper for OpenClaw
- `task-state/` — release-prep notes and operational state

## Quick start

1. Create a venv and install dependencies:

```bash
python3 -m venv .venv-transcribe
. .venv-transcribe/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt
```

2. Export the required env vars:

```bash
export GROQ_API_KEY=your_key_here
export OPENCLAW_TRANSCRIBE_BACKEND=groq
export OPENCLAW_TRANSCRIBE_GROQ_MODEL=whisper-large-v3-turbo
export OPENCLAW_TRANSCRIBE_GROQ_TIER=free
export OPENCLAW_TRANSCRIBE_VENV=/absolute/path/to/.venv-transcribe
```

3. Run a local transcription:

```bash
./bin/transcribe-media ./sample.mp3 --output-format json --timestamps
```

4. Or transcribe a YouTube URL:

```bash
./bin/transcribe-from-youtube 'https://www.youtube.com/watch?v=...'
```

## Requirements

- `python3`
- `curl`
- `ffmpeg`
- `yt-dlp`
- `GROQ_API_KEY`

## Notes on standalone publication

This repo is publishable and now avoids exposing `GROQ_API_KEY` in process arguments during Groq requests. The plugin is still the most coupled layer because it expects this checkout layout, but the core engine is already usable on its own.

## Docs

- `docs/SETUP.md`
- `docs/USAGE.md`
- `docs/CONFIG.md`
- `docs/ARCHITECTURE.md`
- `docs/TROUBLESHOOTING.md`
- `docs/AGENT_FEEDING.md`
