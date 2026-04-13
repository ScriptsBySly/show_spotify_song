import tkinter as tk
from tkinter import ttk

import spotipy

from get_spotify_song import create_spotify_client, format_ms


class SpotifyGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Spotify Now Playing")
        self.root.geometry("520x220")
        self.root.resizable(False, False)

        self.sp = create_spotify_client()
        self.is_playing = None

        self.song_var = tk.StringVar(value="Song: ")
        self.artist_var = tk.StringVar(value="Artist: ")
        self.time_var = tk.StringVar(value="Time: ")
        self.status_var = tk.StringVar(value="Status: Ready")

        self._build_ui()
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

        self.refresh()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        song_label = ttk.Label(container, textvariable=self.song_var, font=("Segoe UI", 12))
        artist_label = ttk.Label(container, textvariable=self.artist_var, font=("Segoe UI", 12))
        time_label = ttk.Label(container, textvariable=self.time_var, font=("Segoe UI", 12))
        status_label = ttk.Label(container, textvariable=self.status_var, font=("Segoe UI", 10))

        song_label.pack(anchor="w", pady=(0, 6))
        artist_label.pack(anchor="w", pady=(0, 6))
        time_label.pack(anchor="w", pady=(0, 12))

        controls = ttk.Frame(container)
        controls.pack(anchor="center", pady=(0, 8))

        self.prev_button = ttk.Button(controls, text="Prev", command=self.previous_track)
        self.play_button = ttk.Button(controls, text="Play", command=self.play_pause)
        self.next_button = ttk.Button(controls, text="Next", command=self.next_track)

        self.prev_button.grid(row=0, column=0, padx=6)
        self.play_button.grid(row=0, column=1, padx=6)
        self.next_button.grid(row=0, column=2, padx=6)

        status_label.pack(anchor="w")

    def set_status(self, message: str) -> None:
        self.status_var.set(f"Status: {message}")

    def update_labels(self, song: str, artist: str, time_text: str) -> None:
        self.song_var.set(f"Song: {song}")
        self.artist_var.set(f"Artist: {artist}")
        self.time_var.set(f"Time: {time_text}")

    def refresh(self) -> None:
        try:
            playback = self.sp.current_playback()
            if not playback:
                self.update_labels("Nothing playing", "", "--:-- / --:--")
                self.is_playing = None
                self.play_button.config(text="Play")
                self.set_status("No active playback")
            elif playback.get("currently_playing_type") == "ad":
                self.update_labels("Advertisement", "Spotify", "--:-- / --:--")
                self.is_playing = playback.get("is_playing")
                self.play_button.config(text="Pause" if self.is_playing else "Play")
                self.set_status("Ad playing")
            else:
                item = playback.get("item") or {}
                artists = ", ".join(artist["name"] for artist in item.get("artists", []))
                title = item.get("name", "Unknown title")
                progress_ms = playback.get("progress_ms") or 0
                duration_ms = item.get("duration_ms") or 0
                time_text = f"{format_ms(progress_ms)} / {format_ms(duration_ms)}"

                self.update_labels(title, artists, time_text)
                self.is_playing = playback.get("is_playing")
                self.play_button.config(text="Pause" if self.is_playing else "Play")
                self.set_status("Playing" if self.is_playing else "Paused")
        except spotipy.SpotifyException as exc:
            self.set_status(f"Error {exc.http_status}: {exc.msg}")
        except Exception as exc:
            self.set_status(f"Unexpected error: {exc}")

        self.root.after(1000, self.refresh)

    def play_pause(self) -> None:
        try:
            if self.is_playing:
                self.sp.pause_playback()
                self.is_playing = False
            else:
                self.sp.start_playback()
                self.is_playing = True
        except spotipy.SpotifyException as exc:
            self.set_status(f"Error {exc.http_status}: {exc.msg}")

    def next_track(self) -> None:
        try:
            self.sp.next_track()
        except spotipy.SpotifyException as exc:
            self.set_status(f"Error {exc.http_status}: {exc.msg}")

    def previous_track(self) -> None:
        try:
            self.sp.previous_track()
        except spotipy.SpotifyException as exc:
            self.set_status(f"Error {exc.http_status}: {exc.msg}")


def main() -> None:
    root = tk.Tk()
    SpotifyGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
