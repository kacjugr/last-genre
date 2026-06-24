A simple web app to look up a Last.fm user's top artists, see tag frequency across them, and get genre recommendations from Gemini.

## Setup

1. Get a Last.fm API key: https://www.last.fm/api/account/create
2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Set your API keys as environment variables (or put them in a `.env` file):

   ```
   export LASTFM_API_KEY=your_lastfm_api_key                 # macOS/Linux
   export LASTFMRECS_GEMINI_API_KEY=your_gemini_api_key

   $env:LASTFM_API_KEY = "your_lastfm_api_key"                # Windows PowerShell
   $env:LASTFMRECS_GEMINI_API_KEY = "your_gemini_api_key"
   ```

   `LASTFMRECS_GEMINI_API_KEY` is only required if you want genre recommendations.

## Usage

```
python app.py
```

Then open http://127.0.0.1:5000 in your browser, enter a Last.fm username, and submit the form.
