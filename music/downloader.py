"""Shared single-video audio downloader for the CLI and local web app."""
import os
import re
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yt_dlp


def output_directory():
    return Path(os.environ.get('YOUTUBE_AUDIO_DIR', '~/karaoke/youtube-download')).expanduser().resolve()


def normalize_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('Enter a YouTube video link.')
    parsed = urlparse(value.strip())
    host = (parsed.hostname or '').lower()
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        raise ValueError('Enter a valid https:// YouTube video link.')
    if host == 'youtu.be':
        video_id = parsed.path.strip('/').split('/')[0]
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        else:
            parts = parsed.path.strip('/').split('/')
            video_id = parts[1] if len(parts) == 2 and parts[0] in ('shorts', 'live', 'embed') else ''
    else:
        raise ValueError('Use a youtube.com or youtu.be video link.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise ValueError('This link does not contain a YouTube video. Playlist-only links are not supported.')
    return f'https://www.youtube.com/watch?v={video_id}'


def runtime_path(name):
    return shutil.which(name) or next((str(p) for p in (Path('/opt/homebrew/bin') / name, Path('/usr/local/bin') / name) if p.is_file()), None)


def dependencies():
    from yt_dlp.version import __version__
    return {'yt_dlp': __version__, 'ffmpeg': runtime_path('ffmpeg'),
            'javascript': runtime_path('deno') or runtime_path('node')}


def download_audio(url, quality='320', progress=None, destination=None):
    url = normalize_url(url)
    if quality not in ('128', '192', '320'):
        raise ValueError('Choose 128, 192, or 320 kbps.')
    directory = Path(destination) if destination else output_directory()
    directory.mkdir(parents=True, exist_ok=True)
    if not runtime_path('ffmpeg'):
        raise RuntimeError('FFmpeg is missing. Install it with brew install ffmpeg, then restart the app.')
    opts = {'noplaylist': True, 'format': 'bestaudio/best',
            'outtmpl': str(directory / '%(title).180B [%(id)s].%(ext)s'),
            'ffmpeg_location': str(Path(runtime_path('ffmpeg')).parent),
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': quality}]}
    for name in ('deno', 'node'):
        path = runtime_path(name)
        if path:
            opts['js_runtimes'] = {name: {'path': path}}
            break
    if 'js_runtimes' not in opts:
        raise RuntimeError('A JavaScript runtime is missing. Install Node.js or Deno, then restart the app.')
    if progress:
        opts['progress_hooks'] = [progress]
        opts['postprocessor_hooks'] = [lambda event: progress({'status': 'converting'})]
        opts['quiet'] = True
        opts['no_warnings'] = True
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info)).with_suffix('.mp3')
    if not path.is_file():
        raise RuntimeError('The download finished without an MP3 file. Check FFmpeg and try again.')
    return {'title': info.get('title', path.stem), 'path': path, 'duration': info.get('duration')}
