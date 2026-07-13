"""Last.fm API helpers."""

import requests

API_URL = "http://ws.audioscrobbler.com/2.0/"

PERIOD_CHOICES = ["overall", "7day", "1month", "3month", "6month", "12month"]

TAGS_PER_ARTIST = 5

NON_GENRE_TAGS = frozenset([
    "seen live",
    "soundtrack",
    "bookmark",
    "love",
    "beautiful",
    "cover",
    "favorites",
    "favorite",
    "mellow",
    "albums i own",
    "awesome",
    "fip",
    "all",
    "sexy",
    "female",
    "melancholic",
    "melancholy",
    "epic",
    "cool",
    "romantic",
    "sad",
    "etherial",
    "dark",
    "live",
    "remix"
])


def get_user_top_artists(username: str, api_key: str, limit: int, period: str) -> list[dict]:
    params = {
        "method": "user.gettopartists",
        "user": username,
        "api_key": api_key,
        "format": "json",
        "limit": limit,
        "period": period,
    }
    response = requests.get(API_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"Last.fm API error {data['error']}: {data.get('message')}")

    return data["topartists"]["artist"]


def get_artist_top_tags(artist_name: str, api_key: str, limit: int = TAGS_PER_ARTIST) -> list[str]:
    params = {
        "method": "artist.gettoptags",
        "artist": artist_name,
        "api_key": api_key,
        "format": "json",
    }
    response = requests.get(API_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"Last.fm API error {data['error']}: {data.get('message')}")

    tags = data["toptags"]["tag"]
    return [
        tag["name"] for tag in tags
        if tag["name"].lower() not in NON_GENRE_TAGS
    ][:limit]


def get_chart_top_tags(api_key: str, limit: int = 200) -> list[dict]:
    params = {
        "method": "chart.gettoptags",
        "api_key": api_key,
        "format": "json",
        "limit": limit,
    }
    response = requests.get(API_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"Last.fm API error {data['error']}: {data.get('message')}")

    tags = data["tags"]["tag"]
    return [
        {"name": tag["name"], "count": tag["taggings"]} for tag in tags
        if tag["name"].lower() not in NON_GENRE_TAGS
    ][:limit]
