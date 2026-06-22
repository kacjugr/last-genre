#!/usr/bin/env python3
"""Fetch a Last.fm user's top listened artists."""

import argparse
import os
import sys
from collections import Counter

import requests
from dotenv import load_dotenv
from google import genai

API_URL = "http://ws.audioscrobbler.com/2.0/"

PERIOD_CHOICES = ["overall", "7day", "1month", "3month", "6month", "12month"]

TAGS_PER_ARTIST = 5

GEMINI_MODEL = "gemini-3.5-flash"


def get_top_artists(username: str, api_key: str, limit: int, period: str) -> list[dict]:
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


def get_top_tags(artist_name: str, api_key: str, limit: int = TAGS_PER_ARTIST) -> list[str]:
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
    return [tag["name"] for tag in tags[:limit]]


def build_gemini_prompt(genre: str, artists: list[dict]) -> str:
    artist_list = "\n".join(f"{i}. {artist['name']}" for i, artist in enumerate(artists, start=1))
    return (
        f"Here is an ordered list of top artists that I listen to:\n{artist_list}\n\n"
        f"I'd like to explore the {genre} genre. Based on this list, recommend artists "
        f"in that genre that I might enjoy."
    )


def ask_gemini(prompt: str, api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv()

    parser = argparse.ArgumentParser(description="Fetch a Last.fm user's top listened artists.")
    parser.add_argument("username", help="Last.fm username")
    parser.add_argument("-n", "--limit", type=int, default=10, help="Number of artists to fetch (default: 10)")
    parser.add_argument(
        "-p", "--period", choices=PERIOD_CHOICES, default="overall",
        help="Time period to consider (default: overall, i.e. all-time)",
    )
    parser.add_argument("-g", "--genre", help="Genre to explore")
    args = parser.parse_args()

    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        print("Error: LASTFM_API_KEY environment variable is not set.", file=sys.stderr)
        return 1

    try:
        artists = get_top_artists(args.username, api_key, args.limit, args.period)
    except requests.RequestException as e:
        print(f"Error: request to Last.fm failed: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not artists:
        print(f"No top artists found for user '{args.username}'.")
        return 0

    tag_counts: Counter = Counter()

    print(f"Top {len(artists)} artists for {args.username} ({args.period}):\n")
    for i, artist in enumerate(artists, start=1):
        try:
            tags = get_top_tags(artist["name"], api_key)
        except (requests.RequestException, RuntimeError) as e:
            print(f"Warning: could not fetch tags for {artist['name']}: {e}", file=sys.stderr)
            tags = []

        tag_counts.update(tags)

        print(f"{i:>2}. {artist['name']} ({artist['playcount']} plays)")

    if tag_counts:
        print("\nTag frequency across these artists:\n")
        for tag, count in tag_counts.most_common():
            print(f"{count:>3}  {tag}")

    if args.genre:
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            print("\nError: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
            return 1

        prompt = build_gemini_prompt(args.genre, artists)
        try:
            reply = ask_gemini(prompt, gemini_api_key)
        except Exception as e:
            print(f"\nError: Gemini request failed: {e}", file=sys.stderr)
            return 1

        print(f"\nGemini recommendations for {args.genre}:\n")
        print(reply)

    return 0


if __name__ == "__main__":
    sys.exit(main())
