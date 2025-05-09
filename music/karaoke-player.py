import pygame
import time
import re
import threading
import tkinter as tk

def display_test():
    root = tk.Tk()
    root.title("Tkinter Test")
    root.geometry("600x200")

    label = tk.Label(root, text="媽媽的淚在流", font=("PingFang TC", 28), wraplength=580, justify="center")
    label.pack(expand=True)

    root.mainloop()
def load_lyrics(file_path):
    lyrics = []
    pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.*)')
    with open(file_path, 'r') as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                minutes = int(match.group(1))
                seconds = float(match.group(2))
                timestamp = minutes * 60 + seconds
                lyrics.append((timestamp, match.group(3)))
    return lyrics


def karaoke_player(audio_file, lyrics, label):
    pygame.mixer.init()
    pygame.mixer.music.load(audio_file)
    pygame.mixer.music.play()

    start_time = time.time()
    index = 0

    while pygame.mixer.music.get_busy():
        current_time = time.time() - start_time
        if index < len(lyrics) and current_time >= lyrics[index][0]:
            line = lyrics[index][1]
            label.config(text=line)
            index += 1
        time.sleep(0.05)


def run_karaoke(audio_file, lyrics_file):
    lyrics = load_lyrics(lyrics_file)
    print(lyrics)

    # Tkinter GUI
    root = tk.Tk()
    root.title("Karaoke Player")
    root.geometry("600x200")
    label = tk.Label(root, text="", font=("PingFang TC", 24), wraplength=580, justify="center")
    label.pack(expand=True)

    # Run the player in a separate thread to avoid blocking GUI
    label.config(text="🎤 正在加载歌词和音乐，请稍候…")
    threading.Thread(target=karaoke_player, args=(audio_file, lyrics, label), daemon=True).start()

    root.mainloop()


# Replace with your actual file paths
run_karaoke("/Users/weizhang/Music/Music/Media.localized/Music/Unknown Artist/Unknown Album/一壺老酒-karaoke.mp3", "/Users/weizhang/Downloads/一壺老酒.lrc")
# run_karaoke("/Users/weizhang/Downloads/一壺老酒.wav", "/Users/weizhang/Downloads/一壺老酒.lrc")
# display_test()