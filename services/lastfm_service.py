"""Self-registers Last.fm into the shared services registry — see
services/registry.py for the registration contract and how to add another service.
"""

import requests

from lastfm import PERIOD_CHOICES, get_user_top_artists
from services.registry import period_choices, top_artists_fns


def get_top_artists(data: dict, context: dict) -> tuple[dict, int]:
    username = (data.get("username") or "").strip()
    period = data.get("period", "overall")
    try:
        limit = int(data.get("limit", 50))
    except (ValueError, TypeError):
        limit = 50

    if not username:
        return {"error": "Please enter a Last.fm username."}, 400
    if period not in PERIOD_CHOICES:
        return {"error": "Invalid period selected."}, 400

    api_key = context.get("lastfm_api_key")
    if not api_key:
        return {"error": "Server is missing the LASTFM_API_KEY environment variable."}, 500

    try:
        artists = get_user_top_artists(username, api_key, limit, period)
    except (requests.RequestException, RuntimeError) as e:
        return {"error": f"Could not fetch top artists: {e}"}, 500

    if not artists:
        return {"error": f"No top artists found for user '{username}'."}, 404

    return {"artists": artists}, 200


top_artists_fns["lastfm"] = get_top_artists
period_choices["lastfm"] = {"choices": PERIOD_CHOICES, "default": "overall"}
