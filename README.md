This is a simple tool to fetch a specific Last.fm user's top X artists over their entire history.

## Setup

1. Get a Last.fm API key: https://www.last.fm/api/account/create
2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Set your API keys as environment variables (or put them in a `.env` file):

   ```
   export LASTFM_API_KEY=your_lastfm_api_key       # macOS/Linux
   export GEMINI_API_KEY=your_gemini_api_key

   $env:LASTFM_API_KEY = "your_lastfm_api_key"      # Windows PowerShell
   $env:GEMINI_API_KEY = "your_gemini_api_key"
   ```

   `GEMINI_API_KEY` is only required when using `-g/--genre`.

## Usage

```
python lastfm_top_artists.py <username> [-n LIMIT] [-p PERIOD] [-g GENRE]
```

- `-n, --limit`: number of artists to fetch (default: 10)
- `-p, --period`: `overall` (default), `7day`, `1month`, `3month`, `6month`, or `12month`
- `-g, --genre`: genre to explore; when set, asks Gemini for recommendations in that genre based on your top artists

Example:

```
python lastfm_top_artists.py rj -n 5 -p 1month -g jazz
```
