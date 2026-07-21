"""Self-registers Spotify into the shared services registry — see
services/registry.py for the registration contract and how to add another service.
"""

import requests
import spotipy

from services.registry import period_choices, top_artists_fns
from spotify import TIME_RANGE_CHOICES, get_client, get_user_top_artists, is_connected


def get_top_artists(data: dict, context: dict) -> tuple[dict, int]:
    time_range = data.get("time_range", "long_term")
    try:
        limit = int(data.get("limit", 50))
    except (ValueError, TypeError):
        limit = 50

    if time_range not in TIME_RANGE_CHOICES:
        return {"error": "Invalid time range selected."}, 400

    oauth = context.get("spotify_oauth")
    if not oauth or not is_connected(oauth):
        return {"error": "Not connected to Spotify.", "needs_auth": True}, 401

    sp = get_client(oauth)
    try:
        artists = get_user_top_artists(sp, limit, time_range)
    except (spotipy.SpotifyException, requests.RequestException) as e:
        return {"error": f"Could not fetch top artists: {e}"}, 500

    if not artists:
        return {"error": "No top artists found for your Spotify account."}, 404

    return {
        "artists": [{"name": a["name"]} for a in artists],
        "display_name": context.get("spotify_display_name") or "your Spotify account",
        "time_range": time_range,
    }, 200


top_artists_fns["spotify"] = get_top_artists
period_choices["spotify"] = TIME_RANGE_CHOICES
