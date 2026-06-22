This is a simple tool to fetch a specific Last.fm user's top X artists over their entire history.

## Setup

1. Get a Last.fm API key: https://www.last.fm/api/account/create
2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Set your API key as an environment variable:

   ```
   export LASTFM_API_KEY=your_api_key_here       # macOS/Linux
   $env:LASTFM_API_KEY = "your_api_key_here"      # Windows PowerShell
   ```

## Usage

```
python lastfm_top_artists.py <username> [-n LIMIT] [-p PERIOD]
```

- `-n, --limit`: number of artists to fetch (default: 10)
- `-p, --period`: `overall` (default), `7day`, `1month`, `3month`, `6month`, or `12month`

Example:

```
python lastfm_top_artists.py rj -n 5 -p 1month
```
