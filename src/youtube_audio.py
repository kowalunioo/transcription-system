#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--output-dir', default='.openclaw/downloads/youtube-audio')
    ap.add_argument('--audio-format', default='m4a')
    return ap.parse_args()


def main() -> int:
    ns = parse_args()
    out_dir = Path(ns.output_dir).resolve()
    ensure_dir(out_dir)
    ytdlp = os.environ.get('OPENCLAW_YTDLP_BIN') or 'yt-dlp'

    info_cmd = [ytdlp, '--dump-single-json', '--no-playlist', ns.url]
    info = run(info_cmd)
    if info.returncode != 0:
        print(json.dumps({'ok': False, 'stage': 'info', 'error': info.stderr or info.stdout}, ensure_ascii=False, indent=2))
        return 1
    meta = json.loads(info.stdout)

    out_template = str(out_dir / '%(title).200B [%(id)s].%(ext)s')
    dl_cmd = [
        ytdlp,
        '--no-playlist',
        '-f', 'bestaudio/best',
        '--extract-audio',
        '--audio-format', ns.audio_format,
        '--output', out_template,
        ns.url,
    ]
    dl = run(dl_cmd)
    if dl.returncode != 0:
        print(json.dumps({'ok': False, 'stage': 'download', 'error': dl.stderr or dl.stdout}, ensure_ascii=False, indent=2))
        return 1

    files = sorted(out_dir.glob(f"*[{meta['id']}].*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print(json.dumps({'ok': False, 'stage': 'locate', 'error': 'Downloaded file not found'}, ensure_ascii=False, indent=2))
        return 1
    fp = files[0]
    payload: dict[str, Any] = {
        'ok': True,
        'source': 'youtube',
        'url': ns.url,
        'id': meta.get('id'),
        'title': meta.get('title'),
        'duration': meta.get('duration'),
        'uploader': meta.get('uploader'),
        'channel': meta.get('channel'),
        'webpage_url': meta.get('webpage_url'),
        'audio_path': str(fp),
        'audio_size_bytes': fp.stat().st_size,
        'format': fp.suffix.lstrip('.').lower(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
