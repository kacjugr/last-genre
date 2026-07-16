1. genre recommendations top tags list.
    Xa. fetch Last.fm top tags, and add them as suggestions options for the genre recommendations input.
    b. maybe a better source than Last.fm, since their tags are not necessarily genres
    c. options for top genres based on overall/year/month?

X2. Add caching last.fm fetch of a user's top artists.
    a. localStorage vs cookies?
    b. it should have a detection mechanism for 'staleness'. something like having an expiration on the check, probably # of minutes/hours equal to the number of plays for the top artist, possibly incrementing if re-fetchs return the same ranked list, and resetting if it does not.

X3. Larger top artist fetch. default to 50?  not sure if this will improve the results from the Gemini prompt

4. Modular popup for recommendations, maybe with some good formatting and album art.

5. Export Gemini recommendation reply to Spotify playlist.

6. host the page somewhere?

7. Spotify OAuth tokens are currently planned to live in Flask's default client-side session (signed cookie, not encrypted) — viewable (not tamperable) by the user via F12 DevTools. Fine for now, but switch to server-side sessions (e.g. Flask-Session with filesystem/Redis backend) before this is anything but single-user/local.

8. The Spotify app is in Development Mode, which only allows logins from users explicitly allowlisted (max 25). Remember to add any new tester's Spotify account before they try to connect, or they'll get a "not registered" error.
    To find/update: https://developer.spotify.com/dashboard -> select the app -> Settings -> Users and Access -> "Add new user" (needs their name + the email on their Spotify account).

9. Fetch full Spotify play history (not just the API's top-items lists) to compute exact lifetime playtime/play counts per track. The Web API can't provide this for anything predating our integration — need the user to request their "Extended streaming history" from Spotify's account privacy settings (Download your data, uncheck "Account data", check "Extended streaming history"). Spotify emails a .zip of JSON files (e.g. Streaming_History_Audio_2018-2026_0.json) within 5-30 days, containing per-play timestamps and millisecond durations since account creation. Would need a one-off import/parse flow since it's not live API data.

10. Improve caching so that we don't fetch the artist genre tags repeatedly