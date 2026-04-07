#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

FREE_TIER_MAX = 25 * 1024 * 1024
DEV_TIER_MAX = 100 * 1024 * 1024
SAFE_FREE = 24 * 1024 * 1024
SAFE_DEV = 95 * 1024 * 1024
DEFAULT_CHUNK_OVERLAP_SECONDS = 8
MIN_CHUNK_SECONDS = 30


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def select_limit(tier: str) -> tuple[int, int]:
    if tier == 'dev':
        return DEV_TIER_MAX, SAFE_DEV
    return FREE_TIER_MAX, SAFE_FREE


def ffprobe_duration_seconds(src: Path) -> float:
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(src),
    ]
    proc = run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or 'ffprobe failed')
    try:
        return float((proc.stdout or '').strip())
    except ValueError as exc:
        raise RuntimeError(f'Unable to parse ffprobe duration for {src}') from exc


def compress_audio(src: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f'{src.stem}.flac'
    cmd = ['ffmpeg', '-y', '-i', str(src), '-ar', '16000', '-ac', '1', '-map', '0:a', '-c:a', 'flac', str(out)]
    proc = run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)
    return out


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('--source', choices=['youtube', 'file'], default='file')
    ap.add_argument('--tier', choices=['free', 'dev'], default=os.environ.get('OPENCLAW_TRANSCRIBE_GROQ_TIER', 'free'))
    ap.add_argument('--language', default=None)
    ap.add_argument('--output-format', default='json', choices=['text', 'json', 'srt', 'all'])
    ap.add_argument('--timestamps', action='store_true', default=True)
    ap.add_argument('--chunk-overlap-seconds', type=int, default=int(os.environ.get('OPENCLAW_TRANSCRIBE_CHUNK_OVERLAP_SECONDS', str(DEFAULT_CHUNK_OVERLAP_SECONDS))))
    return ap.parse_args()


def build_chunk_run_key(selected_path: Path, ns, final_size: int, duration_seconds: float) -> str:
    payload = {
        'selected_path': str(selected_path),
        'selected_size_bytes': final_size,
        'selected_mtime_ns': selected_path.stat().st_mtime_ns,
        'tier': ns.tier,
        'language': ns.language,
        'output_format': ns.output_format,
        'timestamps': ns.timestamps,
        'duration_seconds': round(duration_seconds, 3),
        'chunk_overlap_seconds': ns.chunk_overlap_seconds,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()[:20]


def estimate_chunk_plan(file_size: int, safe_limit: int, duration_seconds: float, overlap_seconds: int) -> list[dict[str, Any]]:
    if duration_seconds <= 0:
        raise RuntimeError('Media duration must be positive for chunking')
    estimated_chunks = max(2, (file_size + safe_limit - 1) // safe_limit)
    chunk_seconds = max(MIN_CHUNK_SECONDS, int(duration_seconds / estimated_chunks) + 1)
    chunks: list[dict[str, Any]] = []
    idx = 0
    start = 0.0
    while start < duration_seconds:
        end = min(duration_seconds, start + chunk_seconds)
        if end <= start:
            break
        chunks.append({
            'index': idx,
            'start_seconds': round(start, 3),
            'end_seconds': round(end, 3),
            'duration_seconds': round(end - start, 3),
        })
        if end >= duration_seconds:
            break
        start = max(0.0, end - overlap_seconds)
        idx += 1
    return chunks


def split_audio_chunks(src: Path, chunks: list[dict[str, Any]], out_dir: Path) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    ext = src.suffix or '.flac'
    for chunk in chunks:
        out_path = out_dir / f"{src.stem}.part{chunk['index']:03d}{ext}"
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(chunk['start_seconds']),
            '-t', str(chunk['duration_seconds']),
            '-i', str(src),
            '-c', 'copy',
            str(out_path),
        ]
        proc = run(cmd)
        if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
            fallback_cmd = [
                'ffmpeg', '-y',
                '-ss', str(chunk['start_seconds']),
                '-t', str(chunk['duration_seconds']),
                '-i', str(src),
                '-ar', '16000', '-ac', '1', '-c:a', 'flac',
                str(out_path.with_suffix('.flac')),
            ]
            fallback_proc = run(fallback_cmd)
            if fallback_proc.returncode != 0:
                raise RuntimeError(f"Chunk split failed for part {chunk['index']}: {fallback_proc.stderr or fallback_proc.stdout or proc.stderr or proc.stdout}")
            out_path = out_path.with_suffix('.flac')
        results.append({
            **chunk,
            'path': str(out_path),
            'size_bytes': out_path.stat().st_size,
        })
    return results


def dedupe_join_text(parts: list[str]) -> str:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    return '\n\n'.join(cleaned)


def merge_segments(chunk_results: list[dict[str, Any]], overlap_seconds: int) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    next_id = 0
    for idx, chunk in enumerate(chunk_results):
        offset = float(chunk['start_seconds'])
        chunk_segments = chunk.get('segments') or []
        drop_before = 0.0
        if idx > 0:
            drop_before = offset + (overlap_seconds / 2)
        for seg in chunk_segments:
            start = float(seg.get('start', 0.0) or 0.0) + offset
            end = float(seg.get('end', 0.0) or 0.0) + offset
            text = str(seg.get('text', '') or '').strip()
            if not text:
                continue
            if idx > 0 and end <= drop_before:
                continue
            merged.append({
                'id': next_id,
                'start': round(start, 3),
                'end': round(end, 3),
                'text': text,
            })
            next_id += 1
    return merged


def write_srt(segments: list[dict[str, Any]], out_path: Path) -> None:
    def fmt(ts: float) -> str:
        ms = int(round(ts * 1000))
        h = ms // 3600000
        ms %= 3600000
        m = ms // 60000
        ms %= 60000
        s = ms // 1000
        ms %= 1000
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{fmt(float(seg['start']))} --> {fmt(float(seg['end']))}")
        lines.append(str(seg.get('text', '')).strip())
        lines.append('')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('\n'.join(lines), encoding='utf-8')


def write_chunked_artifacts(run_dir: Path, payload: dict[str, Any]) -> dict[str, str]:
    run_dir.mkdir(parents=True, exist_ok=True)
    text_path = run_dir / 'transcript.txt'
    json_path = run_dir / 'transcript.json'
    srt_path = run_dir / 'transcript.srt'

    text_path.write_text(payload.get('text', ''), encoding='utf-8')
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    write_srt(payload.get('segments') or [], srt_path)

    return {
        'text': str(text_path),
        'json': str(json_path),
        'srt': str(srt_path),
    }


def transcribe_single(root: Path, selected_path: Path, ns) -> dict[str, Any]:
    tx_cmd = [str(root / 'bin/transcribe-media'), str(selected_path), '--output-format', ns.output_format]
    if ns.timestamps:
        tx_cmd.append('--timestamps')
    if ns.language:
        tx_cmd.extend(['--language', ns.language])
    tx = run(tx_cmd)
    if tx.returncode != 0:
        raise RuntimeError(tx.stdout or tx.stderr or 'Transcription failed')
    return json.loads(tx.stdout)


def transcribe_with_chunking(root: Path, selected_path: Path, ns, max_limit: int, safe_limit: int, download_meta: dict[str, Any], preprocessing: dict[str, Any] | None, final_size: int) -> dict[str, Any]:
    duration_seconds = ffprobe_duration_seconds(selected_path)
    run_key = build_chunk_run_key(selected_path, ns, final_size, duration_seconds)
    chunk_root = root / '.openclaw' / 'chunked-transcripts' / run_key
    aggregate_json = chunk_root / 'transcript.json'

    if aggregate_json.exists():
        cached = json.loads(aggregate_json.read_text(encoding='utf-8'))
        cached['cached'] = True
        return cached

    plan = estimate_chunk_plan(final_size, safe_limit, duration_seconds, ns.chunk_overlap_seconds)
    chunk_dir = chunk_root / 'chunks'
    piece_dir = chunk_root / 'pieces'
    chunk_files = split_audio_chunks(selected_path, plan, piece_dir)

    chunk_results: list[dict[str, Any]] = []
    for chunk in chunk_files:
        if chunk['size_bytes'] > max_limit:
            raise RuntimeError(f"Chunk {chunk['index']} still exceeds hard limit: {chunk['size_bytes']} > {max_limit}")
        chunk_tx = transcribe_single(root, Path(chunk['path']), ns)
        chunk_results.append({
            **chunk,
            'transcription': chunk_tx,
            'segments': chunk_tx.get('segments') or [],
            'text': chunk_tx.get('text', ''),
            'artifacts': chunk_tx.get('artifacts') or {},
            'cache_key': chunk_tx.get('cache_key'),
            'cached': bool(chunk_tx.get('cached')),
        })

    merged_segments = merge_segments(chunk_results, ns.chunk_overlap_seconds)
    merged_text = dedupe_join_text([c.get('text', '') for c in chunk_results])

    payload: dict[str, Any] = {
        'ok': True,
        'source': ns.source,
        'tier': ns.tier,
        'chunked': True,
        'cached': False,
        'groq_limits': {
            'max_limit_bytes': max_limit,
            'safe_limit_bytes': safe_limit,
        },
        'download': download_meta,
        'preprocessing': preprocessing,
        'selected_input_path': str(selected_path),
        'selected_input_size_bytes': final_size,
        'duration_seconds': duration_seconds,
        'chunk_overlap_seconds': ns.chunk_overlap_seconds,
        'chunk_plan': chunk_files,
        'transcription': {
            'ok': True,
            'backend': 'groq',
            'input_path': str(selected_path),
            'task': 'transcribe',
            'timestamps': ns.timestamps,
            'word_timestamps': False,
            'cached': False,
            'chunked': True,
            'text': merged_text,
            'segments': merged_segments,
            'raw_response': {
                'chunk_count': len(chunk_results),
                'chunked': True,
            },
            'chunk_runs': [
                {
                    'index': c['index'],
                    'start_seconds': c['start_seconds'],
                    'end_seconds': c['end_seconds'],
                    'duration_seconds': c['duration_seconds'],
                    'path': c['path'],
                    'size_bytes': c['size_bytes'],
                    'cached': c['cached'],
                    'cache_key': c.get('cache_key'),
                    'artifacts': c.get('artifacts') or {},
                }
                for c in chunk_results
            ],
            'cache_key': run_key,
        },
    }
    artifacts = write_chunked_artifacts(chunk_root, payload['transcription'])
    payload['transcription']['artifacts'] = artifacts
    payload['aggregate_artifacts'] = artifacts
    payload['transcription']['language'] = next((c['transcription'].get('language') for c in chunk_results if c.get('transcription')), ns.language)
    payload['transcription']['model'] = next((c['transcription'].get('model') for c in chunk_results if c.get('transcription')), None)
    payload['transcription']['duration'] = duration_seconds
    payload['transcription']['raw_response']['chunks_dir'] = str(chunk_dir)
    chunk_dir.mkdir(parents=True, exist_ok=True)
    for c in chunk_results:
        chunk_json = chunk_dir / f"chunk-{c['index']:03d}.json"
        chunk_json.write_text(json.dumps(c['transcription'], ensure_ascii=False, indent=2), encoding='utf-8')
    aggregate_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return payload


def main() -> int:
    ns = parse_args()
    max_limit, safe_limit = select_limit(ns.tier)
    root = Path(__file__).resolve().parents[1]

    if ns.source == 'youtube':
        dl = run([str(root / 'bin/download-youtube-audio'), ns.input])
        if dl.returncode != 0:
            print(dl.stdout or dl.stderr)
            return 1
        downloaded = json.loads(dl.stdout)
        media_path = Path(downloaded['audio_path'])
        download_meta: dict[str, Any] = downloaded
    else:
        media_path = Path(ns.input).expanduser().resolve()
        download_meta = {'source': 'file', 'audio_path': str(media_path)}

    if not media_path.exists():
        print(json.dumps({'ok': False, 'error': f'Media not found: {media_path}'}, ensure_ascii=False, indent=2))
        return 1

    original_size = media_path.stat().st_size
    selected_path = media_path
    preprocessing = None

    if original_size > safe_limit:
        try:
            compressed = compress_audio(media_path, root / '.openclaw' / 'preprocessed')
            preprocessing = {'applied': True, 'original_size_bytes': original_size, 'compressed_path': str(compressed), 'compressed_size_bytes': compressed.stat().st_size}
            selected_path = compressed
        except Exception as exc:
            print(json.dumps({'ok': False, 'error': f'Preprocess failed: {exc}'}, ensure_ascii=False, indent=2))
            return 1

    final_size = selected_path.stat().st_size
    try:
        if final_size > max_limit:
            payload = transcribe_with_chunking(root, selected_path, ns, max_limit, safe_limit, download_meta, preprocessing, final_size)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        transcript = transcribe_single(root, selected_path, ns)
        payload = {
            'ok': True,
            'source': ns.source,
            'tier': ns.tier,
            'chunked': False,
            'groq_limits': {
                'max_limit_bytes': max_limit,
                'safe_limit_bytes': safe_limit,
            },
            'download': download_meta,
            'preprocessing': preprocessing,
            'selected_input_path': str(selected_path),
            'selected_input_size_bytes': final_size,
            'transcription': transcript,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            'ok': False,
            'error': str(exc),
            'tier': ns.tier,
            'max_limit_bytes': max_limit,
            'safe_limit_bytes': safe_limit,
            'selected_path': str(selected_path),
            'selected_size_bytes': final_size,
            'chunking_attempted': final_size > max_limit,
        }, ensure_ascii=False, indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
