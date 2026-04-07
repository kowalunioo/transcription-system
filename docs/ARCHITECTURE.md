# Architecture

## Current layers

1. `bin/transcribe-media`
   - stable entrypoint
   - resolves the Python runtime
   - keeps the interface stable for agents and humans

2. `src/transcribe_backend.py`
   - Groq-only backend
   - calls Groq Whisper via `curl` multipart upload
   - writes reusable artifacts
   - returns machine-readable JSON

3. `openclaw-transcribe-plugin/`
   - OpenClaw plugin wrapper exposing `transcribe_media`
   - delegates execution to the stable CLI wrapper
   - keeps the agent-side interface stable even if backend internals evolve

4. `skills/universal-transcription/`
   - universal reusable guidance for any agent or workflow

## Current pipeline behavior

- normal-sized media goes through single-pass transcription
- oversized media is first compressed to mono 16k FLAC when needed
- if the compressed file still exceeds the Groq hard limit, the pipeline automatically splits it into overlapping chunks, transcribes each chunk, and merges the results back into one aggregate transcript
- chunked runs write aggregate artifacts plus per-chunk JSON outputs for debugging and reuse

## Planned extensions

- SDK-based Groq transport as an alternative to curl
- diarization
- speaker labels
- transcript registry/index
- translation presets
- real-time transcription mode
