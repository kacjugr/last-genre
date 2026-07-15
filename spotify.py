"""Spotify API helpers.

Unlike Last.fm, Spotify has no public "look up any user's top artists"
endpoint. A user must authorize this app (OAuth 2.0 authorization code
flow, scope `user-top-read`) before we can read their top items.
"""

import requests
from requests.auth import HTTPBasicAuth

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_URL = "https://api.spotify.com/v1"

SCOPES = "user-top-read"

TIME_RANGE_CHOICES = ["short_term", "medium_term", "long_term"]

# Spotify caps `limit` at 50 per request; fetch more via `offset` pagination.
MAX_PAGE_SIZE = 50


def build_authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": state,
    }
    request = requests.Request("GET", AUTHORIZE_URL, params=params).prepare()
    return request.url


def exchange_code_for_token(code: str, redirect_uri: str, client_id: str, client_secret: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    response = requests.post(
        TOKEN_URL, data=data, auth=HTTPBasicAuth(client_id, client_secret), timeout=10
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(refresh_token: str, client_id: str, client_secret: str) -> dict:
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = requests.post(
        TOKEN_URL, data=data, auth=HTTPBasicAuth(client_id, client_secret), timeout=10
    )
    response.raise_for_status()
    return response.json()


def get_current_user(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{API_URL}/me", headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"Spotify API error {data['error'].get('status')}: {data['error'].get('message')}")

    return data


def _get_user_top_items(item_type: str, access_token: str, limit: int, time_range: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    items: list[dict] = []
    offset = 0

    while len(items) < limit:
        params = {
            "limit": min(MAX_PAGE_SIZE, limit - len(items)),
            "time_range": time_range,
            "offset": offset,
        }
        response = requests.get(f"{API_URL}/me/top/{item_type}", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise RuntimeError(f"Spotify API error {data['error'].get('status')}: {data['error'].get('message')}")

        page_items = data["items"]
        items.extend(page_items)

        if not data.get("next") or not page_items:
            break
        offset += len(page_items)

    return items


def get_user_top_artists(access_token: str, limit: int, time_range: str) -> list[dict]:
    return _get_user_top_items("artists", access_token, limit, time_range)


def get_user_top_tracks(access_token: str, limit: int, time_range: str) -> list[dict]:
    return _get_user_top_items("tracks", access_token, limit, time_range)
