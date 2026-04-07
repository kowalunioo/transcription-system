#!/usr/bin/env python3
import argparse
import hashlib
import json
import mimetypes
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SUPPORTED_EXTS = {'.mp4', '.mkv', '.mov', '.mp3', '.wav', '.m4a', '.webm'}


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


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
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{fmt(float(seg['start']))} --> {fmt(float(seg['end']))}")
        lines.append(str(seg.get('text', '')).strip())
        lines.append('')
    ensure_parent(out_path)
    out_path.write_text('\n'.join(lines), encoding='utf-8')


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--language', default=None)
    ap.add_argument('--output-format', default='text', choices=['text', 'json', 'srt', 'all'])
    ap.add_argument('--timestamps', action='store_true', default=False)
    ap.add_argument('--no-timestamps', dest='timestamps', action='store_false')
    ap.add_argument('--diarization', action='store_true', default=False)
    ap.add_argument('--task', default='transcribe', choices=['transcribe', 'translate'])
    ap.add_argument('--model', default=os.environ.get('OPENCLAW_TRANSCRIBE_GROQ_MODEL', 'whisper-large-v3-turbo'))
    ap.add_argument('--backend', default=os.environ.get('OPENCLAW_TRANSCRIBE_BACKEND', 'groq'), choices=['groq'])
    ap.add_argument('--output-dir', default=os.environ.get('OPENCLAW_TRANSCRIBE_OUTPUT_DIR', '.openclaw/transcripts'))
    ap.add_argument('--temp-dir', default=os.environ.get('OPENCLAW_TRANSCRIBE_TEMP_DIR', '.openclaw/transcripts/tmp'))
    ap.add_argument('--no-cache', dest='cache', action='store_false', default=True)
    ap.add_argument('--word-timestamps', action='store_true', default=False)
    ns = ap.parse_args()
    return ns


def build_cache_key(path_hash: str, ns) -> str:
    payload = {
        'src_hash': path_hash,
        'language': ns.language,
        'output_format': ns.output_format,
        'timestamps': ns.timestamps,
        'task': ns.task,
        'model': ns.model,
        'backend': ns.backend,
        'word_timestamps': ns.word_timestamps,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()[:20]


def transcribe_with_groq(src: Path, ns) -> dict[str, Any]:
    api_key = os.environ.get('GROQ_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('GROQ_API_KEY is not available in the runtime environment')
    if subprocess.run(['curl', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        raise RuntimeError('curl is required for the Groq backend')

    cmd = [
        'curl', '-sS', 'https://api.groq.com/openai/v1/audio/transcriptions',
        '-H', f'Authorization: Bearer {api_key}',
        '-F', f'file=@{src}',
        '-F', f'model={ns.model}',
        '-F', f'response_format=verbose_json',
        '-F', 'temperature=0',
    ]
    if ns.language:
        cmd.extend(['-F', f'language={ns.language}'])
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f'curl failed: {result.stderr.strip() or result.stdout.strip()}')
    try:
        data = json.loads(result.stdout)
    except Exception as exc:
        raise RuntimeError(f'Groq returned non-JSON output: {exc}; body={result.stdout[:500]}')
    if isinstance(data, dict) and data.get('error'):
        raise RuntimeError(f'Groq API error: {data}')
    return data


def main() -> int:
    ns = parse_args()
    src = Path(ns.path).expanduser().resolve()
    if not src.exists():
        eprint(f'Input not found: {src}')
        return 2
    if src.suffix.lower() not in SUPPORTED_EXTS:
        eprint(f'Unsupported input type: {src.suffix}')
        return 2
    if ns.diarization:
        eprint('Diarization is not implemented yet for the Groq backend.')

    path_hash = sha256_file(src)
    output_dir = Path(ns.output_dir)
    cache_key = build_cache_key(path_hash, ns)
    run_dir = (output_dir / cache_key).resolve()
    text_path = run_dir / 'transcript.txt'
    json_path = run_dir / 'transcript.json'
    srt_path = run_dir / 'transcript.srt'

    if ns.cache and text_path.exists() and json_path.exists() and (ns.output_format != 'srt' or srt_path.exists()):
        payload = json.loads(json_path.read_text(encoding='utf-8'))
        payload['cached'] = True
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    try:
        raw = transcribe_with_groq(src, ns)
        text = raw.get('text', '') if isinstance(raw, dict) else ''
        segments = []
        if isinstance(raw, dict):
            for idx, seg in enumerate(raw.get('segments', []) or []):
                if not isinstance(seg, dict):
                    continue
                segments.append({
                    'id': seg.get('id', idx),
                    'start': float(seg.get('start', 0.0) or 0.0),
                    'end': float(seg.get('end', 0.0) or 0.0),
                    'text': seg.get('text', ''),
                })
        payload = {
            'ok': True,
            'backend': 'groq',
            'input_path': str(src),
            'model': ns.model,
            'language': raw.get('language') if isinstance(raw, dict) else ns.language,
            'duration': raw.get('duration') if isinstance(raw, dict) else None,
            'task': ns.task,
            'timestamps': ns.timestamps,
            'word_timestamps': ns.word_timestamps,
            'cached': False,
            'text': text,
            'segments': segments,
            'raw_response': raw,
            'artifacts': {
                'text': str(text_path),
                'json': str(json_path),
                'srt': str(srt_path),
            },
            'cache_key': cache_key,
        }
        ensure_parent(text_path)
        text_path.write_text(text, encoding='utf-8')
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        if ns.output_format in {'srt', 'all'} or ns.timestamps:
            write_srt(segments, srt_path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        eprint(f'Transcription failed: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
