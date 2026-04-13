import argparse
import os
import time
from datetime import timedelta
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth


def format_ms(ms: int) -> str:
    seconds = int(ms / 1000)
    return str(timedelta(seconds=seconds))


def get_current_track(sp: spotipy.Spotify) -> str:
    playback = sp.current_playback()
    if not playback:
        return "Nothing is currently playing."

    if playback.get("currently_playing_type") == "ad":
        return "Spotify is currently playing an ad."

    item = playback.get("item")
    if not item:
        return "Nothing is currently playing."

    artists = ", ".join(artist["name"] for artist in item.get("artists", []))
    title = item.get("name", "Unknown title")
    album = item.get("album", {}).get("name", "Unknown album")

    progress_ms = playback.get("progress_ms")
    duration_ms = item.get("duration_ms")
    progress = (
        f"{format_ms(progress_ms)} / {format_ms(duration_ms)}"
        if progress_ms is not None and duration_ms is not None
        else "Unknown progress"
    )

    is_playing = playback.get("is_playing")
    status = "Playing" if is_playing else "Paused"

    return f"{status}: {artists} - {title}  |  {album}  |  {progress}"


def load_config() -> None:
    project_root = Path(__file__).resolve().parent
    config_path = project_root.parent / "config" / "spotify.config"
    if not config_path.exists():
        return

    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and value:
            os.environ.setdefault(key, value)


def is_escape_pressed() -> bool:
    try:
        import msvcrt
    except ImportError:
        return False

    if msvcrt.kbhit():
        key = msvcrt.getch()
        return key == b"\x1b"
    return False


def create_spotify_client() -> spotipy.Spotify:
    load_config()

    auth_manager = SpotifyOAuth(
        scope=(
            "user-read-currently-playing "
            "user-read-playback-state "
            "user-modify-playback-state"
        ),
        open_browser=True,
        cache_path=".cache-spotify",
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show the current song playing in Spotify."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between updates.",
    )
    args = parser.parse_args()

    sp = create_spotify_client()

    try:
        while True:
            line = get_current_track(sp)
            print(f"\r{line:<120}", end="", flush=True)

            if is_escape_pressed():
                print("\nStopped.")
                break

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
