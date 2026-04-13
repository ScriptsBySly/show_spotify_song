import argparse
import io
import time
import tkinter as tk
from urllib.request import urlopen

import spotipy
from PIL import Image, ImageDraw, ImageTk
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
except Exception:
    CLSCTX_ALL = None
    AudioUtilities = None
    IAudioMeterInformation = None

from get_spotify_song import create_spotify_client, format_ms


class SpotifyGUI:
    def __init__(self, root: tk.Tk, enable_visualizer: bool) -> None:
        self.root = root
        self.root.title("Spotify Now Playing")
        self.root.resizable(False, False)

        self.sp = create_spotify_client()
        self.is_playing = None

        self.song_var = tk.StringVar(value="Song: ")
        self.artist_var = tk.StringVar(value="Artist: ")
        self.time_var = tk.StringVar(value="Time: ")
        self.status_var = tk.StringVar(value="Status: Ready")
        self._album_art = None
        self._album_art_url = None
        self._art_image_id = None
        self._button_images: list[ImageTk.PhotoImage] = []
        self._viz_bars: list[int] = []
        self._viz_running = enable_visualizer
        self._meter_session = None
        self._meter_last_scan = 0.0

        self._build_ui()
        self._fit_to_content()
        self.root.bind("<Escape>", lambda _event: self.root.destroy())

        self.refresh()
        if self._viz_running:
            self.animate_visualizer()

    def _build_ui(self) -> None:
        self.root.configure(bg="#d6dbe6")

        title_bar = tk.Frame(self.root, bg="#7fa7d9", relief="raised", bd=1)
        title_bar.pack(fill="x")
        title_label = tk.Label(
            title_bar,
            text="Now Playing",
            fg="white",
            bg="#7fa7d9",
            font=("Tahoma", 10, "bold"),
            padx=8,
            pady=4,
            anchor="w",
        )
        title_label.pack(fill="x")

        container = tk.Frame(self.root, bg="#d6dbe6")
        container.pack(fill="both", expand=True, padx=10, pady=8)

        display = tk.Frame(container, bg="#f0f3f8", bd=2, relief="sunken")
        display.pack(fill="x", padx=4, pady=4)

        display_row = tk.Frame(display, bg="#f0f3f8")
        display_row.pack(fill="x")

        self.art_canvas = tk.Canvas(
            display_row,
            width=96,
            height=96,
            bg="#d0d6e2",
            highlightthickness=0,
            bd=2,
            relief="ridge",
        )
        self.art_canvas.pack(side="left", padx=8, pady=8)

        text_stack = tk.Frame(display_row, bg="#f0f3f8")
        text_stack.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=8)

        song_label = tk.Label(
            text_stack,
            textvariable=self.song_var,
            bg="#f0f3f8",
            fg="#1b1b1b",
            font=("Tahoma", 11, "bold"),
            anchor="w",
        )
        artist_label = tk.Label(
            text_stack,
            textvariable=self.artist_var,
            bg="#f0f3f8",
            fg="#1b1b1b",
            font=("Tahoma", 11),
            anchor="w",
        )

        song_label.pack(anchor="w", pady=(6, 4), fill="x")
        artist_label.pack(anchor="w", pady=(0, 6), fill="x")

        led_frame = tk.Frame(text_stack, bg="#1a1a1a", bd=2, relief="sunken")
        led_frame.pack(anchor="w", pady=(0, 2), fill="x")
        led_label = tk.Label(
            led_frame,
            textvariable=self.time_var,
            bg="#1a1a1a",
            fg="#7CFF6B",
            font=("Courier New", 12, "bold"),
            padx=6,
            pady=2,
            anchor="w",
        )
        led_label.pack(fill="x")

        controls = tk.Frame(container, bg="#d6dbe6")
        controls.pack(anchor="center", pady=(6, 4))

        self.prev_button = self._create_oval_button(controls, "<<", self.previous_track, width=60)
        self.play_button = self._create_oval_button(controls, "Play", self.play_pause, width=76)
        self.next_button = self._create_oval_button(controls, ">>", self.next_track, width=60)

        self.prev_button.grid(row=0, column=0, padx=8)
        self.play_button.grid(row=0, column=1, padx=8)
        self.next_button.grid(row=0, column=2, padx=8)

        if self._viz_running:
            viz_frame = tk.Frame(container, bg="#0e0f12", bd=2, relief="sunken")
            viz_frame.pack(fill="x", padx=6, pady=(4, 6))
            self.viz_canvas = tk.Canvas(
                viz_frame,
                width=520,
                height=46,
                bg="#0e0f12",
                highlightthickness=0,
            )
            self.viz_canvas.pack(padx=4, pady=4)
            self._init_visualizer()

        status_bar = tk.Frame(self.root, bg="#c8d1e0", relief="sunken", bd=1)
        status_bar.pack(fill="x", side="bottom")
        status_label = tk.Label(
            status_bar,
            textvariable=self.status_var,
            bg="#c8d1e0",
            fg="#1b1b1b",
            font=("Tahoma", 9),
            anchor="w",
            padx=6,
            pady=3,
        )
        status_label.pack(fill="x")

    def _fit_to_content(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        min_width = 560
        if width < min_width:
            width = min_width
        self.root.geometry(f"{width}x{height}")

    def set_status(self, message: str) -> None:
        self.status_var.set(f"Status: {message}")

    def update_labels(self, song: str, artist: str, time_text: str) -> None:
        self.song_var.set(f"Song: {song}")
        self.artist_var.set(f"Artist: {artist}")
        self.time_var.set(f"Time: {time_text}")

    def _create_oval_button(
        self, parent: tk.Widget, text: str, command, width: int = 64
    ) -> tk.Frame:
        height = 34
        frame = tk.Frame(parent, bg="#d6dbe6")
        canvas = tk.Canvas(
            frame,
            width=width,
            height=height,
            bg="#d6dbe6",
            highlightthickness=0,
        )
        canvas.pack()

        fill = "#e6e6e6"
        outline = "#7b7b7b"
        shadow = "#b0b0b0"
        oval = canvas.create_oval(2, 2, width - 2, height - 2, fill=fill, outline=outline)
        canvas.create_oval(4, 4, width - 4, height - 4, outline=shadow)
        label = canvas.create_text(
            width // 2,
            height // 2,
            text=text,
            fill="#1a1a1a",
            font=("Tahoma", 9, "bold"),
        )

        def on_press(_event):
            canvas.itemconfigure(oval, fill="#d2d2d2")

        def on_release(_event):
            canvas.itemconfigure(oval, fill=fill)
            command()

        canvas.tag_bind(oval, "<ButtonPress-1>", on_press)
        canvas.tag_bind(label, "<ButtonPress-1>", on_press)
        canvas.tag_bind(oval, "<ButtonRelease-1>", on_release)
        canvas.tag_bind(label, "<ButtonRelease-1>", on_release)
        canvas.configure(cursor="hand2")
        return frame

    def _build_gradient_button(self, width: int, height: int) -> ImageTk.PhotoImage:
        top = (248, 248, 248)
        mid = (212, 212, 212)
        bottom = (168, 168, 168)
        img = Image.new("RGB", (width, height), top)
        draw = ImageDraw.Draw(img)
        for y in range(height):
            if y < height * 0.55:
                ratio = y / max(1, int(height * 0.55))
                color = tuple(
                    int(top[i] + (mid[i] - top[i]) * ratio) for i in range(3)
                )
            else:
                ratio = (y - height * 0.55) / max(1, int(height * 0.45))
                color = tuple(
                    int(mid[i] + (bottom[i] - mid[i]) * ratio) for i in range(3)
                )
            draw.line([(0, y), (width, y)], fill=color)
        draw.rectangle((0, 0, width - 1, height - 1), outline=(120, 120, 120))
        return ImageTk.PhotoImage(img)

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
                self._update_album_art(item)

                self.update_labels(title, artists, time_text)
                self.is_playing = playback.get("is_playing")
                self._set_play_button_text("Pause" if self.is_playing else "Play")
                self.set_status("Playing" if self.is_playing else "Paused")
        except spotipy.SpotifyException as exc:
            self.set_status(f"Error {exc.http_status}: {exc.msg}")
        except Exception as exc:
            self.set_status(f"Unexpected error: {exc}")

        self.root.after(1000, self.refresh)

    def _get_spotify_peak(self) -> float:
        if AudioUtilities is None or IAudioMeterInformation is None:
            return 0.0

        now = time.time()
        if self._meter_session is None or now - self._meter_last_scan > 3.0:
            self._meter_session = self._find_spotify_session()
            self._meter_last_scan = now

        if self._meter_session is None:
            return 0.0

        try:
            meter = self._meter_session._ctl.QueryInterface(IAudioMeterInformation)
            return float(meter.GetPeakValue())
        except Exception:
            return 0.0

    def _find_spotify_session(self):
        try:
            sessions = AudioUtilities.GetAllSessions()
        except Exception:
            return None

        for session in sessions:
            process = session.Process
            if process and process.name().lower() == "spotify.exe":
                return session
        return None

    def _init_visualizer(self) -> None:
        self.viz_canvas.delete("all")
        self._viz_bars.clear()
        bar_count = 32
        width = int(self.viz_canvas["width"])
        height = int(self.viz_canvas["height"])
        gap = 4
        bar_width = max(4, (width - gap * (bar_count + 1)) // bar_count)
        x = gap
        for _ in range(bar_count):
            bar = self.viz_canvas.create_rectangle(
                x,
                height - 2,
                x + bar_width,
                height - 2,
                fill="#41f46b",
                outline="",
            )
            self._viz_bars.append(bar)
            x += bar_width + gap

    def animate_visualizer(self) -> None:
        if not self._viz_running:
            return
        try:
            height = int(self.viz_canvas["height"])
            peak = self._get_spotify_peak()
            for idx, bar in enumerate(self._viz_bars):
                idle = 0.08
                movement = 0.15 if self.is_playing else 0.08
                base = (idx % 8) / 8.0
                wobble = (time.time() * 1.8 + idx * 0.7) % 1.0
                level = idle + (movement * (base + wobble)) + (peak * 0.85)
                level = min(1.0, max(0.05, level))
                bar_height = int(level * (height - 6))
                self.viz_canvas.coords(
                    bar,
                    self.viz_canvas.coords(bar)[0],
                    height - 2 - bar_height,
                    self.viz_canvas.coords(bar)[2],
                    height - 2,
                )
        finally:
            self.root.after(120, self.animate_visualizer)

    def play_pause(self) -> None:
        try:
            if self.is_playing:
                self.sp.pause_playback()
                self.is_playing = False
            else:
                self.sp.start_playback()
                self.is_playing = True
            self._set_play_button_text("Pause" if self.is_playing else "Play")
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

    def _set_play_button_text(self, text: str) -> None:
        canvas = self.play_button.winfo_children()[0]
        items = canvas.find_all()
        for item in items:
            if canvas.type(item) == "text":
                canvas.itemconfigure(item, text=text)
                break

    def _update_album_art(self, item: dict) -> None:
        images = item.get("album", {}).get("images", [])
        if not images:
            return
        url = images[0].get("url")
        if not url or url == self._album_art_url:
            return
        try:
            with urlopen(url, timeout=4) as response:
                data = response.read()
            image = Image.open(io.BytesIO(data)).convert("RGB")
            image = image.resize((96, 96), Image.LANCZOS)
            self._album_art = ImageTk.PhotoImage(image)
            self._album_art_url = url
            if self._art_image_id is None:
                self._art_image_id = self.art_canvas.create_image(
                    48, 48, image=self._album_art
                )
            else:
                self.art_canvas.itemconfigure(self._art_image_id, image=self._album_art)
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Spotify now playing GUI."
    )
    parser.add_argument(
        "--visualizer",
        action="store_true",
        help="Enable the visualizer strip.",
    )
    args = parser.parse_args()

    root = tk.Tk()
    SpotifyGUI(root, enable_visualizer=args.visualizer)
    root.mainloop()


if __name__ == "__main__":
    main()
