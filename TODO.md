1. genre recommendations top tags list.
    a. maybe a better source than Last.fm, since their tags are not necessarily genres
    b. options for top genres based on overall/year/month?

2. Modular popup for recommendations, maybe with some good formatting and album art.

3. Export Gemini recommendation reply to Spotify playlist.

4. host the page somewhere?

5. Spotify OAuth tokens are currently planned to live in Flask's default client-side session (signed cookie, not encrypted) — viewable (not tamperable) by the user via F12 DevTools. Fine for now, but switch to server-side sessions (e.g. Flask-Session with filesystem/Redis backend) before this is anything but single-user/local.

6. The Spotify app is in Development Mode, which only allows logins from users explicitly allowlisted (max 25). Remember to add any new tester's Spotify account before they try to connect, or they'll get a "not registered" error.
    To find/update: https://developer.spotify.com/dashboard -> select the app -> Settings -> Users and Access -> "Add new user" (needs their name + the email on their Spotify account).

7. Fetch full Spotify play history (not just the API's top-items lists) to compute exact lifetime playtime/play counts per track. The Web API can't provide this for anything predating our integration — need the user to request their "Extended streaming history" from Spotify's account privacy settings (Download your data, uncheck "Account data", check "Extended streaming history"). Spotify emails a .zip of JSON files (e.g. Streaming_History_Audio_2018-2026_0.json) within 5-30 days, containing per-play timestamps and millisecond durations since account creation. Would need a one-off import/parse flow since it's not live API data.

8. Maybe move the gemini response parsing to server-side.  Would require error handling there, and a different return code on failure.