import yt_dlp


ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320',
    }],
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
url = 'https://www.youtube.com/watch?v=6wr1Uaylbv8&list=RD6wr1Uaylbv8&start_radio=1'
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])