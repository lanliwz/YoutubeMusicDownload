"""Download one YouTube video as MP3, optionally passing a URL on the CLI."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from music.downloader import download_audio


def main():
    parser = argparse.ArgumentParser(description='Download a single YouTube video as MP3')
    parser.add_argument('url', nargs='?', default='https://www.youtube.com/watch?v=ACG8aJHcZ_M')
    parser.add_argument('--quality', choices=('128', '192', '320'), default='320')
    args = parser.parse_args()
    result = download_audio(args.url, args.quality)
    print(f"Saved: {result['path']}")


if __name__ == '__main__':
    main()
