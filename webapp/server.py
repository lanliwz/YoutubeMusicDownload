"""Local HTTP app. Run with python -m webapp.server."""
import argparse
import hashlib
import json
import mimetypes
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from music.downloader import dependencies, download_audio, normalize_url, output_directory

STATIC = Path(__file__).parent / 'static'


class DownloadManager:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else output_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.jobs = {}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1)

    def create(self, url, quality):
        url = normalize_url(url)
        if quality not in ('128', '192', '320'):
            raise ValueError('Choose a valid audio quality.')
        with self.lock:
            active = [j for j in self.jobs.values() if j['status'] not in ('complete', 'error')]
            if any(j['url'] == url for j in active):
                raise ValueError('This video is already in your queue.')
            if len(active) >= 10:
                raise ValueError('Your queue is full. Wait for a download to finish.')
            job = {'id': secrets.token_hex(8), 'url': url, 'quality': quality, 'status': 'queued',
                   'title': 'Waiting in queue', 'progress': 0, 'created': time.time(), 'error': None}
            self.jobs[job['id']] = job
            # Keep bounded history without dropping active tasks.
            for old in sorted(self.jobs.values(), key=lambda j: j['created'])[:-100]:
                if old['status'] in ('complete', 'error'):
                    self.jobs.pop(old['id'], None)
        self.executor.submit(self.run, job['id'])
        return job['id']

    def update(self, job_id, **values):
        with self.lock:
            self.jobs[job_id].update(values)

    def run(self, job_id):
        with self.lock:
            job = dict(self.jobs[job_id])
        self.update(job_id, status='extracting', title='Finding your audio')

        def progress(event):
            if event['status'] in ('finished', 'converting'):
                self.update(job_id, status='converting', progress=100)
            elif event['status'] == 'downloading':
                total = event.get('total_bytes') or event.get('total_bytes_estimate') or 0
                percent = min(100, event.get('downloaded_bytes', 0) / total * 100) if total else 0
                self.update(job_id, status='downloading', progress=round(percent, 1),
                            title=event.get('info_dict', {}).get('title', 'Downloading audio'))
        try:
            result = download_audio(job['url'], job['quality'], progress, self.directory)
            self.update(job_id, status='complete', progress=100, title=result['title'],
                        file_id=self.file_id(result['path']))
        except Exception as exc:
            self.update(job_id, status='error', error=str(exc).replace('\x1b', '')[:1500])

    @staticmethod
    def file_id(path):
        return hashlib.sha256(path.name.encode()).hexdigest()[:24]

    def library(self):
        files = []
        for path in self.directory.glob('*.mp3'):
            if path.is_symlink() or not path.is_file():
                continue
            stat = path.stat()
            files.append({'id': self.file_id(path), 'title': path.stem, 'filename': path.name,
                          'bytes': stat.st_size, 'modified': stat.st_mtime})
        return sorted(files, key=lambda item: item['modified'], reverse=True)

    def resolve(self, file_id):
        return next((self.directory / f['filename'] for f in self.library() if f['id'] == file_id), None)

    def snapshot(self):
        with self.lock:
            jobs = [dict(j) for j in sorted(self.jobs.values(), key=lambda j: j['created'], reverse=True)]
        return {'jobs': jobs, 'library': self.library()}


def make_handler(manager):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def send(self, status, body, content_type='application/json'):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {'error': 'Use the local app address.'})
            path = unquote(urlparse(self.path).path)
            if path == '/api/state':
                return self.send(200, manager.snapshot())
            if path == '/api/config':
                return self.send(200, {'token': token, 'directory': str(manager.directory), 'dependencies': dependencies()})
            if path.startswith('/audio/'):
                file = manager.resolve(path.split('/')[-1])
                if not file:
                    return self.send(404, {'error': 'Audio file not found.'})
                return self.audio(file, 'download' in urlparse(self.path).query)
            assets = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}
            if path not in assets:
                return self.send(404, {'error': 'Not found.'})
            file = STATIC / assets[path]
            return self.send(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or 'text/plain')

        def audio(self, file, attachment):
            size = file.stat().st_size
            start, end = 0, size - 1
            request_range = self.headers.get('Range')
            if request_range:
                import re
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', request_range)
                if not match or not any(match.groups()):
                    return self.send(416, {'error': 'Invalid byte range.'})
                first, last = match.groups()
                if first:
                    start = int(first)
                    end = min(int(last), size - 1) if last else size - 1
                else:
                    start = max(0, size - int(last))
                if start > end or start >= size:
                    return self.send(416, {'error': 'Range outside audio file.'})
            self.send_response(206 if request_range else 200)
            self.send_header('Content-Type', 'audio/mpeg')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(end - start + 1))
            if request_range:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            if attachment:
                from urllib.parse import quote
                self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(file.name))
            self.end_headers()
            try:
                with file.open('rb') as stream:
                    stream.seek(start)
                    remaining = end - start + 1
                    while remaining > 0:
                        chunk = stream.read(min(65536, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            if not self.valid_host() or self.headers.get('X-App-Token') != token:
                return self.send(403, {'error': 'Refresh the app before downloading.'})
            if self.path != '/api/downloads':
                return self.send(404, {'error': 'Not found.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    raise ValueError('Invalid request size.')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Invalid download request.')
                job_id = manager.create(data.get('url'), data.get('quality', '320'))
                return self.send(202, {'id': job_id})
            except (ValueError, TypeError) as exc:
                return self.send(400, {'error': str(exc)})

    return Handler


def main():
    parser = argparse.ArgumentParser(description='Your local YouTube audio library')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    manager = DownloadManager()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(manager))
    print(f'Audio Studio is ready at http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        manager.executor.shutdown(wait=True)


if __name__ == '__main__':
    main()
