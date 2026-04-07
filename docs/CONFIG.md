# Config

## Env vars

- `GROQ_API_KEY`
- `OPENCLAW_TRANSCRIBE_BACKEND=groq`
- `OPENCLAW_TRANSCRIBE_GROQ_MODEL=whisper-large-v3-turbo`
- `OPENCLAW_TRANSCRIBE_GROQ_TIER=free|dev`
- `OPENCLAW_TRANSCRIBE_OUTPUT_DIR`
- `OPENCLAW_TRANSCRIBE_TEMP_DIR`
- `OPENCLAW_TRANSCRIBE_VENV`
- `OPENCLAW_YTDLP_BIN`

## Practical tier planning

- free tier hard limit: `25 MB`
- dev tier hard limit: `100 MB`
- recommended safe upload target:
  - free: `24 MB`
  - dev: `95 MB`

## Plugin config example

```json
{
  "plugins": {
    "entries": {
      "openclaw-transcribe": {
        "enabled": true,
        "config": {
          "defaultModel": "whisper-large-v3-turbo",
          "defaultLanguage": null,
          "defaultOutputFormat": "json",
          "defaultTimestamps": true,
          "defaultSource": "file",
          "defaultTier": "free",
          "chunkOverlapSeconds": 8,
          "outputDir": ".openclaw/transcripts",
          "tempDir": ".openclaw/transcripts/tmp"
        }
      }
    }
  }
}
```
