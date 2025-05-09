import tkinter as tk
from tkinter import filedialog, messagebox
import pygame
import time
import re
import os

class KaraokeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎤 Karaoke Lyric Tool")
        self.root.geometry("700x300")

        self.lyrics = []
        self.timestamps = []
        self.index = 0
        self.start_time = None
        self.audio_file = None
        self.lyric_file = None
        self.prev_label = tk.Label(self.root, text="", font=("PingFang TC", 16), fg="gray")
        self.prev_label.pack()

        self.curr_label = tk.Label(self.root, text="", font=("PingFang TC", 24, "bold"), fg="blue")
        self.curr_label.pack(pady=10)

        self.next_label = tk.Label(self.root, text="", font=("PingFang TC", 16), fg="#888")
        self.next_label.pack()

        self.create_widgets()
        pygame.mixer.init()
        self.root.bind("<space>", lambda e: self.mark_timestamp())

    def create_widgets(self):
        self.audio_btn = tk.Button(self.root, text="🎵 Select Audio", command=self.select_audio)
        self.audio_btn.pack(pady=5)

        self.lyric_btn = tk.Button(self.root, text="📄 Load Lyrics File (.txt or .lrc)", command=self.load_lyrics)
        self.lyric_btn.pack(pady=5)

        self.start_btn = tk.Button(self.root, text="🕒 Start Timing Mode", command=self.start_timing, state="disabled")
        self.start_btn.pack(pady=5)

        self.preview_btn = tk.Button(self.root, text="🎬 Preview Karaoke", command=self.preview_karaoke, state="disabled")
        self.preview_btn.pack(pady=5)

        self.line_label = tk.Label(self.root, text="請載入歌詞和音樂...", font=("PingFang TC", 22), wraplength=650, justify="center", fg="blue")
        self.line_label.pack(pady=20)

        self.mark_btn = tk.Button(self.root, text="✅ Mark (or press Spacebar)", command=self.mark_timestamp, state="disabled")
        self.mark_btn.pack()

    def select_audio(self):
        file = filedialog.askopenfilename(title="Select Audio File", filetypes=[("Audio", "*.mp3 *.wav")])
        if file:
            self.audio_file = file
            messagebox.showinfo("Audio Loaded", f"Loaded:\n{os.path.basename(file)}")
            self.check_ready()

    def load_lyrics(self):
        file = filedialog.askopenfilename(title="Select Lyrics File", filetypes=[("Lyrics", "*.txt *.lrc")])
        if file:
            self.lyric_file = file
            with open(file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if any(re.match(r"\[\d+:\d+\.\d+\]", line) for line in lines):
                # LRC format
                self.timestamps = self.parse_lrc(lines)
                self.lyrics = [lyr for _, lyr in self.timestamps]
                messagebox.showinfo("LRC Lyrics Loaded", f"{len(self.lyrics)} lines with timestamps.")
            else:
                # Plain text format
                self.lyrics = [line.strip() for line in lines if line.strip()]
                messagebox.showinfo("Plain Lyrics Loaded", f"{len(self.lyrics)} lines loaded (no timestamps).")
            self.check_ready()

    def check_ready(self):
        if self.audio_file and self.lyrics:
            self.start_btn.config(state="normal")
            self.preview_btn.config(state="normal")

    def start_timing(self):
        if not self.audio_file or not self.lyrics:
            return
        self.index = 0
        self.timestamps = []
        self.start_time = time.time()
        self.line_label.config(text=self.lyrics[0])
        self.mark_btn.config(state="normal")
        self.start_btn.config(state="disabled")
        pygame.mixer.music.load(self.audio_file)
        pygame.mixer.music.play()

    def mark_timestamp(self):
        if self.index >= len(self.lyrics):
            return
        current_time = time.time() - self.start_time
        self.timestamps.append((current_time, self.lyrics[self.index]))
        self.index += 1

        if self.index < len(self.lyrics):
            self.line_label.config(text=self.lyrics[self.index])
        else:
            self.line_label.config(text="🎉 Finished!")
            self.mark_btn.config(state="disabled")
            pygame.mixer.music.stop()
            self.save_lrc()

    def save_lrc(self):
        filename = filedialog.asksaveasfilename(defaultextension=".lrc", filetypes=[("LRC files", "*.lrc")])
        if not filename:
            return
        with open(filename, "w", encoding="utf-8") as f:
            for t, line in self.timestamps:
                m = int(t // 60)
                s = t % 60
                f.write(f"[{m:02d}:{s:05.2f}]{line}\n")
        messagebox.showinfo("Saved", f"LRC file saved to:\n{filename}")

    def parse_lrc(self, lines):
        result = []
        pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.*)')
        for line in lines:
            match = pattern.match(line)
            if match:
                minutes = int(match.group(1))
                seconds = float(match.group(2))
                timestamp = minutes * 60 + seconds
                result.append((timestamp, match.group(3).strip()))
        result.sort(key=lambda x: x[0])
        return result

    def preview_karaoke(self):
        if not self.timestamps or not self.audio_file:
            messagebox.showerror("Error", "No timestamps loaded. Load a valid .lrc file first.")
            return
        self.index = 0
        self.start_time = time.time()
        pygame.mixer.music.load(self.audio_file)
        pygame.mixer.music.play()
        self.line_label.config(text="🎬 播放中...")
        self.root.after(50, self.update_preview)

    def update_preview(self):
        if self.index >= len(self.timestamps):
            self.prev_label.config(text=self.curr_label.cget("text"))
            self.curr_label.config(text="🎉 播放完畢", fg="green")
            self.next_label.config(text="")
            return

        current_time = time.time() - self.start_time
        next_time, next_line = self.timestamps[self.index]

        if current_time >= next_time:
            # shift lines
            self.prev_label.config(text=self.curr_label.cget("text"))
            self.curr_label.config(text=next_line)
            self.index += 1
            if self.index < len(self.timestamps):
                self.next_label.config(text=self.timestamps[self.index][1])
            else:
                self.next_label.config(text="")

        self.root.after(50, self.update_preview)

# Run app
if __name__ == "__main__":
    root = tk.Tk()
    app = KaraokeApp(root)
    root.mainloop()