import yt_dlp


import os

# Ensure the output directory exists
output_dir = "/Users/weizhang/karaoke/youtube-download"
os.makedirs(output_dir, exist_ok=True)

ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320',
    }]
}
# Waltz Music
# https://www.youtube.com/watch?v=YoRTOkQWe7c
# https://www.youtube.com/watch?v=pSyefchC84w
# https://www.youtube.com/watch?v=luQmhN5Zfvk
# https://www.youtube.com/watch?v=Tg7N7ewWlxM
# https://www.youtube.com/watch?v=24eNBufKuBg
# https://www.youtube.com/watch?v=OvMdVvop_cY
# https://www.youtube.com/watch?v=w7vJOT6vqHQ
# https://www.youtube.com/watch?v=LIEtwVhqlkk
#############################################
url = 'https://www.youtube.com/watch?v=Bwca-g2qHCs'
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])