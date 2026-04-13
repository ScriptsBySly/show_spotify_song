# show_spotify_song
A python script that shows the current song playing in Spotify.

## Setup
1. Create a Spotify app and grab the Client ID/Secret.
2. Set these environment variables (or put them in `..\config\spotify.config`):
   - `SPOTIPY_CLIENT_ID`
   - `SPOTIPY_CLIENT_SECRET`
   - `SPOTIPY_REDIRECT_URI` (example: `http://127.0.0.1:8888/callback`)

## Config File (Optional)
Create `H:\Projects\Scripts_By_Sly\config\spotify.config` with:
```
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```
3. Install dependencies: `pip install -r requirements.txt`

## Run
Run the app (GUI, live updating, press Esc to quit):
```
python main.py
```

The GUI includes Play/Pause, Next, and Previous buttons.

The visualizer now reads Spotify's audio session (Windows desktop app) for real-time peaks.
