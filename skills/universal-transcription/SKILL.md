---
name: universal-transcription
description: Audio/video transcription workflow for OpenClaw agents using a reusable `transcribe_media` interface backed by Groq Whisper. Use when a user provides or references a local media file that should be transcribed, subtitled, summarized, searched, or handed off to another domain agent. Works for investing, content creation, research, interviews, meetings, lectures, podcasts, and general media analysis.
---

# Universal Transcription

Use the transcription system before doing downstream media analysis.

## Core workflow

1. Recognize media inputs that should be transcribed first.
2. Prefer the `transcribe_media` tool when available.
3. Fallback to the local CLI wrapper at `transcription-system/bin/transcribe-media` when the plugin tool is unavailable.
4. Reuse cached transcript artifacts when they already exist for the same file/settings.
5. Preserve timestamps when the downstream task involves citations, clip selection, fact checking, subtitles, or structured extraction.
6. Pass the resulting transcript text or JSON into the active domain workflow.

## Tool interface

Preferred tool call shape:

- `path`: local media path
- `language`: optional language hint
- `output_format`: `text` | `json` | `srt` | `all`
- `timestamps`: boolean
- `diarization`: reserved for future support
- `task`: `transcribe` | `translate`
- `model`: optional model override
- `word_timestamps`: optional detailed timing mode

## CLI fallback

```bash
./transcription-system/bin/transcribe-media <path> --output-format json --timestamps
```

The CLI returns JSON to stdout and writes artifact files to the transcript cache directory.

## Output handling

- Use `text` for summarization or agent handoff when raw text is enough.
- Use `json` when timestamps, segments, and metadata matter.
- Use `srt` when subtitles are explicitly requested.
- Use `all` when future reuse is likely.

## Avoid unnecessary retranscription

Before re-running, check whether the prior tool result or artifact paths already satisfy the task.
Prefer cache reuse unless the user asks for a different model, language, task, or output detail.

## Domain examples

### Investing

- Transcribe earnings calls, management interviews, podcasts, and macro briefings.
- Then extract thesis changes, guidance changes, risk signals, and timestamped evidence.

### Content creation

- Transcribe talking-head videos, interviews, livestream clips, or podcast episodes.
- Then derive hooks, titles, clip moments, quote cards, and short-form ideas.

### General analysis

- Transcribe any interview, lecture, or meeting recording.
- Then summarize, create action items, or hand transcript text to a specialist agent.

## Future extensions

The interface is intentionally stable.
The backend can later gain diarization, speaker labels, chunking, transcript stores, translation presets, and real-time transcription without changing how agents invoke it.
