# Changelog

## 0.1.1 - 2026-04-07

### Security / transport hardening
- replaced the Groq `curl` subprocess call with a native Python HTTP request so `GROQ_API_KEY` is no longer exposed through process arguments during transcription

## 0.1.0 - 2026-04-07

### Added
- local-first transcription pipeline for audio/video and YouTube sources
- Groq Whisper backend via `curl`
- preprocessing to mono 16 kHz FLAC for oversized media
- automatic chunking and aggregate transcript merging
- reusable transcript artifacts: `txt`, `json`, `srt`
- OpenClaw plugin wrapper: `openclaw-transcribe-plugin`
- docs for setup, usage, configuration, troubleshooting, architecture, and agent-feeding workflows

### Changed
- plugin wrapper now resolves repo root from `import.meta.url` instead of relying on workspace-relative assumptions
- documentation now reflects the real runtime coupling more honestly and is clone-oriented

### Security / publishing
- root `.gitignore` keeps env files, caches, transcript artifacts, downloads, venvs, and bytecode out of publication
- no hardcoded API keys or credentials are included in the published surface

### Notes
- the plugin remains intentionally thin and shells out to the local pipeline
- the current Groq transport still exposes the bearer token to local process inspection through the `curl` command line while a request is running
