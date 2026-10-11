import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from music.downloader import normalize_url
from webapp.server import DownloadManager, make_handler


class URLTests(unittest.TestCase):
    def test_video_links_strip_playlist(self):
        for url in ('https://youtu.be/ACG8aJHcZ_M?t=10', 'https://www.youtube.com/watch?v=ACG8aJHcZ_M&list=RDACG8aJHcZ_M', 'https://music.youtube.com/watch?v=ACG8aJHcZ_M', 'https://youtube.com/shorts/ACG8aJHcZ_M'):
            self.assertEqual(normalize_url(url), 'https://www.youtube.com/watch?v=ACG8aJHcZ_M')

    def test_rejects_untrusted_or_playlist_only_links(self):
        for url in ('http://localhost/test', 'https://youtube.com.evil.com/watch?v=ACG8aJHcZ_M', 'https://youtube.com/playlist?list=123', None, 'file:///etc/passwd', 'https://youtube.com/watch?v=invalid'):
            with self.assertRaises(ValueError):
                normalize_url(url)


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.manager = DownloadManager(self.temp.name)
        self.audio = Path(self.temp.name) / 'Example [ACG8aJHcZ_M].mp3'
        self.audio.write_bytes(b'0123456789')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.manager))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.manager.executor.shutdown(wait=True)
        self.temp.cleanup()

    def test_library_stream_seek_and_download(self):
        with urlopen(self.base + '/api/state') as response:
            library = json.load(response)['library']
        path = '/audio/' + library[0]['id']
        with urlopen(Request(self.base + path, headers={'Range': 'bytes=2-5'})) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(response.read(), b'2345')
        with urlopen(self.base + path + '?download=1') as response:
            self.assertIn('attachment', response.headers['Content-Disposition'])
        with self.assertRaises(HTTPError) as exc:
            urlopen(self.base + '/audio/../../etc/passwd')
        self.assertEqual(exc.exception.code, 404)

    def test_missing_token_and_invalid_url(self):
        request = Request(self.base + '/api/downloads', data=b'{}', headers={'Content-Type': 'application/json'})
        with self.assertRaises(HTTPError) as exc:
            urlopen(request)
        self.assertEqual(exc.exception.code, 403)
        with urlopen(self.base + '/api/config') as response:
            token = json.load(response)['token']
        request = Request(self.base + '/api/downloads', data=b'{"url":"https://example.com"}', headers={'Content-Type':'application/json', 'X-App-Token':token})
        with self.assertRaises(HTTPError) as exc:
            urlopen(request)
        self.assertEqual(exc.exception.code, 400)

    def test_job_completion_and_failure(self):
        with patch('webapp.server.download_audio', return_value={'title':'Example', 'path':self.audio}):
            job_id = self.manager.create('https://youtu.be/ACG8aJHcZ_M', '320')
            self.manager.executor.submit(lambda: None).result(timeout=5)
        self.assertEqual(self.manager.jobs[job_id]['status'], 'complete')
        self.assertEqual(self.manager.jobs[job_id]['file_id'], self.manager.file_id(self.audio))
        with patch('webapp.server.download_audio', side_effect=RuntimeError('Video unavailable')):
            job_id = self.manager.create('https://youtu.be/ACG8aJHcZ_M', '192')
            self.manager.executor.submit(lambda: None).result(timeout=5)
        self.assertEqual(self.manager.jobs[job_id]['status'], 'error')
        self.assertEqual(self.manager.jobs[job_id]['error'], 'Video unavailable')

    def test_rejects_duplicate_queued_job(self):
        with patch.object(self.manager.executor, 'submit'):
            self.manager.create('https://youtu.be/ACG8aJHcZ_M', '320')
            with self.assertRaises(ValueError):
                self.manager.create('https://youtube.com/watch?v=ACG8aJHcZ_M&list=abc', '320')


if __name__ == '__main__':
    unittest.main()
