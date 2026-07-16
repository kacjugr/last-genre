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
from spotipy.oauth2 import SpotifyOAuth

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
