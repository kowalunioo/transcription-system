# Agent Feeding Guide

This document describes the practical stack for feeding agents with audio, video, and YouTube material.

## Stack

- `transcribe_media` — acquisition
- `ingest_media_knowledge` — digestion and routing
- `agent_head_*` files/tools — durable storage
- `lossless-claw` — compact context and later detail retrieval

## Principle

Do **not** dump raw transcripts into durable memory by default.

Use this default policy:
- transcript artifacts live in the transcription system
- compact/working recall belongs to lossless-claw
- durable takeaways belong in agent-heads

## Recommended default flow

1. Transcribe the source.
2. Register it as a source.
3. Extract summary + key points + follow-ups.
4. Write candidate notes first.
5. Promote durable pieces later.

## Tool call shape

Example parameters for `ingest_media_knowledge`:

```json
{
  "path": "https://www.youtube.com/watch?v=...",
  "source": "youtube",
  "agentKey": "main",
  "knowledgeMode": "candidate",
  "writeSources": true,
  "writeSummary": true,
  "writeBacklog": true,
  "timestamps": true,
  "outputFormat": "json",
  "maxItems": 8,
  "sharedPromotion": "none"
}
```

## Knowledge modes

### `candidate`
Safest.
Creates candidate notes for later review.

### `auto`
Balanced.
Writes only obvious low-risk metadata directly, leaves ambiguous content as candidates.

### `direct`
Aggressive.
Writes durable entries immediately. Use only for short, trusted, low-ambiguity material.

## File mapping

- `SOURCES.md` — source registry + provenance
- `KNOWLEDGE.md` — distilled knowledge
- `BACKLOG.md` — follow-ups and open questions
- `MEMORY.md` — only if you explicitly choose to store raw transcript text or very durable context

## lossless-claw role

Use lossless-claw for:
- compact transcript/session summaries
- later retrieval of detail
- search → inspect → expand workflows

Do not use agent-heads as a substitute for transcript storage.

## Bridge convention

When media is ingested, preserve the same identifiers across systems:
- `sourceId` from agent-heads
- transcript `cache_key`
- `selected_input_path`
- artifact paths (`txt`, `json`, `srt`)
- stable media title

Those fields are the join keys for later recall. If a transcript-derived fact shows up again in chat, search lossless-claw first using the media title or source ID, then inspect and expand as needed.

Recommended search flow:
1. `lcm_grep` for the title, source ID, or a unique phrase
2. `lcm_describe` for the relevant summary or stored file
3. `lcm_expand_query` when the answer was compacted away

## Practical examples

### Podcast / lecture
- `knowledgeMode: "candidate"`
- write to `SOURCES.md`
- create candidate knowledge notes
- maybe backlog for future exploration

### Meeting / voice note
- `knowledgeMode: "auto"`
- write source + candidate notes
- promote decisions or tasks after review

### Very short trusted memo
- `knowledgeMode: "direct"`
- direct write to `KNOWLEDGE.md` or `BACKLOG.md`

## Warnings

- `writeTranscript: true` can bloat `MEMORY.md` fast
- YouTube and long recordings should almost always start in candidate mode
- shared promotion should stay explicit and rare
