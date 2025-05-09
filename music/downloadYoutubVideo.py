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
url = 'https://music.youtube.com/watch?v=LNFuroF-evk&list=PLhrZMOVonpjVQBcLfWWNg_4pq_Nc4Cf2t'
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])