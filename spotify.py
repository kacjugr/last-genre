"""Spotify API helpers, built on spotipy.

Unlike Last.fm, Spotify has no public "look up any user's top artists"
endpoint. A user must authorize this app (OAuth 2.0 authorization code
flow, scope `user-top-read`) before we can read their top items.

Token storage/refresh is handled by spotipy's FlaskSessionCacheHandler,
which reads/writes the token dict under session["token_info"] and
transparently refreshes an expired access token whenever it's used.
"""

import spotipy
from spotipy.cache_handler import FlaskSessionCacheHandler
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

SCOPE = "user-top-read"

TIME_RANGE_CHOICES = ["short_term", "medium_term", "long_term"]

# Spotify caps `limit` at 50 per request; fetch more via pagination.
MAX_PAGE_SIZE = 50

# The session key spotipy's FlaskSessionCacheHandler stores the token under.
TOKEN_SESSION_KEY = "token_info"


def make_oauth(session, client_id: str, client_secret: str, redirect_uri: str) -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        cache_handler=FlaskSessionCacheHandler(session),
        show_dialog=False,
    )


def is_connected(oauth: SpotifyOAuth) -> bool:
    return oauth.validate_token(oauth.cache_handler.get_cached_token()) is not None


def get_client(oauth: SpotifyOAuth) -> spotipy.Spotify:
    return spotipy.Spotify(auth_manager=oauth)


def get_current_user(sp: spotipy.Spotify) -> dict:
    return sp.me()


def _get_user_top_items(sp: spotipy.Spotify, item_type: str, limit: int, time_range: str) -> list[dict]:
    method = getattr(sp, f"current_user_top_{item_type}")
    items: list[dict] = []

    results = method(limit=min(MAX_PAGE_SIZE, limit), time_range=time_range)
    items.extend(results["items"])
    while results.get("next") and len(items) < limit:
        results = sp.next(results)
        items.extend(results["items"])

    return items[:limit]


def get_user_top_artists(sp: spotipy.Spotify, limit: int, time_range: str) -> list[dict]:
    return _get_user_top_items(sp, "artists", limit, time_range)


def get_user_top_tracks(sp: spotipy.Spotify, limit: int, time_range: str) -> list[dict]:
    return _get_user_top_items(sp, "tracks", limit, time_range)


# --- Catalog search for Gemini-recommendation artwork ---------------------------------
#
# Looking up artist/album images is a public-catalog search, not a per-user read, so it
# uses the Client Credentials flow (app-only auth) instead of the user's OAuth session —
# artwork should show up even for a Last.fm user who's never connected Spotify.


def get_client_credentials_client(client_id: str, client_secret: str) -> spotipy.Spotify:
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth_manager)


def _smallest_image(images: list[dict] | None) -> str | None:
    return images[-1]["url"] if images else None


def search_artist_image(sp: spotipy.Spotify, artist_name: str) -> str | None:
    try:
        results = sp.search(q=artist_name, type="artist", limit=1)
    except spotipy.SpotifyException:
        return None
    items = results.get("artists", {}).get("items", [])
    return _smallest_image(items[0].get("images")) if items else None


def search_album_image(sp: spotipy.Spotify, artist_name: str, album_title: str) -> str | None:
    try:
        results = sp.search(q=f'artist:"{artist_name}" album:"{album_title}"', type="album", limit=1)
    except spotipy.SpotifyException:
        return None
    items = results.get("albums", {}).get("items", [])
    return _smallest_image(items[0].get("images")) if items else None


def _normalize_albums(recommendation: dict) -> list[dict]:
    """The prompt asks Gemini for an 'albums' array, but tolerate 'recommended_albums'
    or a single 'album' object too, in case a reply still comes back that way.
    """
    for key in ("albums", "recommended_albums"):
        albums = recommendation.get(key)
        if isinstance(albums, list):
            return [a for a in albums if isinstance(a, dict)]
    single = recommendation.get("album")
    return [single] if isinstance(single, dict) else []


def get_recommendation_artwork(sp: spotipy.Spotify, recommendations: list[dict]) -> list[dict]:
    """For each Gemini artist recommendation, look up its Spotify artist image and each
    recommended album's cover art, in the same order as `recommendations`. A missing or
    unmatched lookup is None rather than an error, so one bad match doesn't sink the batch.
    """
    results = []
    for rec in recommendations:
        name = (rec.get("name") or "").strip() if isinstance(rec, dict) else ""
        artist_image = search_artist_image(sp, name) if name else None

        albums = []
        for album in _normalize_albums(rec) if isinstance(rec, dict) else []:
            title = album.get("title")
            image = search_album_image(sp, name, title) if (name and title) else None
            albums.append({"title": title, "image": image})

        results.append({"name": name, "image": artist_image, "albums": albums})
    return results
