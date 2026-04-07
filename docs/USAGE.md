# Usage

## Tool / plugin behavior

The `transcribe_media` plugin tool now calls the full media pipeline instead of the raw single-file backend. That means agents get the same interface for:

- local files
- YouTube URLs (`source: "youtube"`)
- normal uploads
- oversized uploads that need preprocessing and chunking

The tool result keeps the full payload in `details`, while the top-level text content is shortened to the most important fields: transcript text, chunked flag, segment count, selected input path, and artifact paths.

## Core CLI

```bash
./bin/transcribe-media ./sample.mp4
./bin/transcribe-media ./sample.mp3 --language en --output-format json
./bin/transcribe-media ./interview.mkv --output-format srt --timestamps
```

## Media pipeline with Groq size planning

```bash
./bin/transcribe-media-pipeline ./local-file.mp4 --source file --tier free
./bin/transcribe-media-pipeline ./local-file.mp4 --source file --tier dev
```

Behavior:
- checks the Groq upload tier limit
- uses a safe upload target below the hard limit
- preprocesses oversized media to mono 16k FLAC when needed
- if the file is still too large after preprocessing, automatically splits it into overlapping chunks, transcribes them separately, and merges them into one aggregate transcript
- writes aggregate transcript artifacts and preserves per-chunk metadata for inspection

## YouTube → audio → transcription

```bash
./bin/download-youtube-audio 'https://www.youtube.com/watch?v=...'
./bin/transcribe-from-youtube 'https://www.youtube.com/watch?v=...' --tier free
./bin/transcribe-from-youtube 'https://www.youtube.com/watch?v=...' --tier dev --language en
```

The YouTube flow:
1. downloads audio-only via `yt-dlp`
2. checks Groq file-size constraints
3. preprocesses when needed
4. chunk-splits automatically if the upload is still too large
5. sends one file or many chunks to Groq Whisper
6. stores transcript artifacts locally

## Groq size plan

- free tier hard limit: `25 MB`
- dev tier hard limit: `100 MB`
- safe target used by the pipeline:
  - free: `24 MB`
  - dev: `95 MB`

If the file still exceeds the hard limit after preprocessing, the pipeline switches into chunked mode automatically. The result payload includes:

- `chunked: true`
- `chunk_plan`: chunk start/end offsets and file paths
- `transcription.chunk_runs`: per-chunk transcription metadata
- `aggregate_artifacts`: merged `txt/json/srt` outputs

## Investing workflow

1. Transcribe earnings call or interview.
2. Feed transcript text or JSON to the investing agent.
3. Ask for thesis extraction, risk flags, guidance deltas, or management tone notes.

## Content creation workflow

1. Transcribe a talking-head video or YouTube source.
2. Preserve timestamps.
3. Use transcript for hooks, shorts ideas, title testing, and clip selection.

## General-purpose analysis workflow

1. Transcribe local media or YouTube audio.
2. Pass transcript into research/analysis flow.
3. Optionally summarize, extract action items, or generate subtitles.
