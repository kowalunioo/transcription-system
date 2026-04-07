# openclaw-transcribe-plugin

OpenClaw plugin that exposes a `transcribe_media` tool for:

- local audio/video files
- YouTube URLs
- automatic preprocessing for oversized files
- automatic chunking + merged transcript artifacts when Groq upload limits are exceeded

It wraps the local transcription pipeline from the sibling `transcription-system` project and keeps the agent-facing tool interface stable.

## What ships here

- plugin metadata for OpenClaw
- a `transcribe_media` tool wrapper
- a stable contract for local file and YouTube transcription
- simple config hooks for venv/script locations and default transcription settings

## Runtime model

The plugin is intentionally thin:

- the real work happens in `../bin/transcribe-media-pipeline`
- the plugin shells out to that pipeline
- the pipeline shells out to the Python backend and `yt-dlp`/`ffmpeg`

That makes this repo easier to publish because the public surface stays small.

## Tool: `transcribe_media`

Parameters:

- `path` — local media path, or YouTube URL when `source: "youtube"`
- `source` — `file` or `youtube`
- `tier` — `free` or `dev`
- `language` — optional language hint
- `output_format` — `text`, `json`, `srt`, or `all`
- `timestamps` — include timestamped segments
- `diarization` — accepted for interface compatibility, not implemented yet
- `task` — `transcribe` or `translate`
- `model` — accepted for interface compatibility
- `word_timestamps` — accepted for interface compatibility
- `chunk_overlap_seconds` — overlap used for chunk merge planning

The tool returns:

- compact top-level result for agents
- full detailed payload under `details`
- artifact paths for generated `.txt`, `.json`, and `.srt`

## Requirements

- `node >= 18`
- `python3`
- `curl`
- `ffmpeg`
- `yt-dlp`
- `GROQ_API_KEY`
- a Python virtualenv with the required packages installed

## Install

From a checkout containing this repo:

```bash
openclaw plugins install -l ./openclaw-transcribe-plugin
openclaw gateway restart
```

## Recommended environment

```bash
export GROQ_API_KEY=your_key_here
export OPENCLAW_TRANSCRIBE_BACKEND=groq
export OPENCLAW_TRANSCRIBE_GROQ_MODEL=whisper-large-v3-turbo
export OPENCLAW_TRANSCRIBE_GROQ_TIER=free
export OPENCLAW_TRANSCRIBE_VENV=/absolute/path/to/.venv-transcribe
```

## Example plugin config

```json
{
  "plugins": {
    "entries": {
      "openclaw-transcribe": {
        "enabled": true,
        "config": {
          "defaultOutputFormat": "json",
          "defaultTimestamps": true,
          "defaultSource": "file",
          "defaultTier": "free",
          "chunkOverlapSeconds": 8
        }
      }
    }
  }
}
```

## Repo shape

This plugin is still coupled to the sibling repo layout because the executable pipeline lives in `../bin/`.

If we want a truly standalone GitHub repo later, the cleanest next step is to vendor the pipeline or publish it as a separate installable package.

## Known gaps

- no diarization yet
- no speaker labels yet
- still shells out to local scripts instead of shipping a self-contained runtime
- package metadata is intentionally minimal

## License

MIT
