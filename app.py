#!/usr/bin/env python3
"""Web app for exploring a Last.fm user's top artists and genre recommendations."""

import json
import os
import secrets
from collections import Counter

import requests
import spotipy
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request, session, stream_with_context, url_for

from gemini import ask_gemini_with_retry_streaming, build_gemini_prompt
from lastfm import PERIOD_CHOICES, get_artist_top_tags, get_chart_top_tags, get_user_top_artists
from spotify import (
    TIME_RANGE_CHOICES,
    TOKEN_SESSION_KEY,
    get_client as get_spotify_client,
    get_client_credentials_client,
    get_current_user as get_spotify_current_user,
    get_recommendation_artwork,
    get_user_top_artists as get_spotify_top_artists,
    is_connected as spotify_is_connected,
    make_oauth as make_spotify_oauth,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

LIMIT_CHOICES = [10, 25, 50, 100, 250, 500]


def _spotify_redirect_uri() -> str:
    return os.environ.get("SPOTIFY_REDIRECT_URI", request.url_root.rstrip("/") + "/spotify/callback")


def _spotify_oauth():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    return make_spotify_oauth(session, client_id, client_secret, _spotify_redirect_uri())


@app.route("/", methods=["GET"])
def index():
    form = {
        "username": "kacjugr",
        "limit": 50,
        "period": "overall",
    }
    oauth = _spotify_oauth()
    return render_template(
        "index.html",
        lastfm_period_choices=PERIOD_CHOICES,
        limit_choices=LIMIT_CHOICES,
        form=form,
        spotify_time_range_choices=TIME_RANGE_CHOICES,
        spotify_connected=bool(oauth and spotify_is_connected(oauth)),
        spotify_display_name=session.get("spotify_display_name") or "",
        spotify_error=request.args.get("spotify_error"),
    )


@app.route("/lastfm/top-artists", methods=["POST"])
def lastfm_top_artists():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    period = data.get("period", "overall")
    try:
        limit = int(data.get("limit", 50))
    except (ValueError, TypeError):
        limit = 50

    if not username:
        return jsonify({"error": "Please enter a Last.fm username."}), 400
    if period not in PERIOD_CHOICES:
        return jsonify({"error": "Invalid period selected."}), 400

    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        return jsonify({"error": "Server is missing the LASTFM_API_KEY environment variable."}), 500

    try:
        artists = get_user_top_artists(username, api_key, limit, period)
    except (requests.RequestException, RuntimeError) as e:
        return jsonify({"error": f"Could not fetch top artists: {e}"}), 500

    if not artists:
        return jsonify({"error": f"No top artists found for user '{username}'."}), 404

    return jsonify({"artists": artists})


@app.route("/artist-tag-counts", methods=["POST"])
def fetch_tag_counts():
    data = request.get_json(silent=True) or {}
    artist_names = data.get("artist_names") or []

    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        return jsonify({"error": "Server is missing the LASTFM_API_KEY environment variable."}), 500

    def generate():
        counts: Counter = Counter()
        for name in artist_names:
            try:
                tags = get_artist_top_tags(name, api_key)
            except Exception:
                tags = []
            counts.update(tags)
            yield f"data: {json.dumps({'artist': name, 'tags': tags, 'tag_counts': counts.most_common()})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/chart-top-tags", methods=["GET"])
def chart_top_tags():
    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        return jsonify({"error": "Server is missing the LASTFM_API_KEY environment variable."}), 500

    try:
        tags = get_chart_top_tags(api_key)
    except (requests.RequestException, RuntimeError) as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"tags": tags})


@app.route("/gemini", methods=["POST"])
def gemini():
    data = request.get_json(silent=True) or {}
    genre = (data.get("genre") or "").strip()
    artist_names = data.get("artists") or []

    if not genre or not artist_names:
        return jsonify({"error": "Missing genre or artists."}), 400

    gemini_api_key = os.environ.get("LASTFMRECS_GEMINI_API_KEY")
    if not gemini_api_key:
        return jsonify({"error": "Server is missing the LASTFMRECS_GEMINI_API_KEY environment variable."}), 500

    prompt = build_gemini_prompt(genre, [{"name": name} for name in artist_names])

    def generate():
        try:
            for event in ask_gemini_with_retry_streaming(prompt, gemini_api_key):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/spotify/artwork", methods=["POST"])
def gemini_artwork():
    data = request.get_json(silent=True) or {}
    recommendations = data.get("recommendations") or []

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return jsonify({"error": "Server is missing Spotify API credentials."}), 500

    sp = get_client_credentials_client(client_id, client_secret)
    artwork = get_recommendation_artwork(sp, recommendations)

    return jsonify({"artwork": artwork})


@app.route("/spotify/login", methods=["GET"])
def spotify_login():
    oauth = _spotify_oauth()
    if not oauth:
        return jsonify({"error": "Server is missing Spotify API credentials."}), 500

    state = secrets.token_urlsafe(16)
    session["spotify_state"] = state
    return redirect(oauth.get_authorize_url(state=state))


@app.route("/spotify/logout", methods=["GET"])
def spotify_logout():
    session.pop(TOKEN_SESSION_KEY, None)
    session.pop("spotify_display_name", None)
    return redirect(url_for("index"))


@app.route("/spotify/callback", methods=["GET"])
def spotify_callback():
    error = request.args.get("error")
    if error:
        return redirect(url_for("index", spotify_error=f"Spotify authorization failed: {error}"))

    state = request.args.get("state")
    if not state or state != session.pop("spotify_state", None):
        return redirect(url_for("index", spotify_error="Spotify login state mismatch. Please try again."))

    oauth = _spotify_oauth()
    if not oauth:
        return redirect(url_for("index", spotify_error="Server is missing Spotify API credentials."))

    code = request.args.get("code")
    if not code:
        return redirect(url_for("index", spotify_error="Spotify did not return an authorization code."))

    try:
        oauth.get_access_token(code, as_dict=False, check_cache=False)
    except (spotipy.SpotifyOauthError, requests.RequestException) as e:
        return redirect(url_for("index", spotify_error=f"Could not connect to Spotify: {e}"))

    try:
        user = get_spotify_current_user(get_spotify_client(oauth))
        session["spotify_display_name"] = user.get("display_name") or user.get("id")
    except (spotipy.SpotifyException, requests.RequestException):
        session["spotify_display_name"] = None

    return redirect(url_for("index"))


@app.route("/spotify/top-artists", methods=["POST"])
def spotify_top_artists():
    data = request.get_json(silent=True) or {}
    time_range = data.get("time_range", "long_term")
    try:
        limit = int(data.get("limit", 50))
    except (ValueError, TypeError):
        limit = 50

    if time_range not in TIME_RANGE_CHOICES:
        return jsonify({"error": "Invalid time range selected."}), 400

    oauth = _spotify_oauth()
    if not oauth or not spotify_is_connected(oauth):
        return jsonify({"error": "Not connected to Spotify.", "needs_auth": True}), 401

    sp = get_spotify_client(oauth)
    try:
        artists = get_spotify_top_artists(sp, limit, time_range)
    except (spotipy.SpotifyException, requests.RequestException) as e:
        return jsonify({"error": f"Could not fetch top artists: {e}"}), 500

    if not artists:
        return jsonify({"error": "No top artists found for your Spotify account."}), 404

    return jsonify({
        "artists": [{"name": a["name"]} for a in artists],
        "display_name": session.get("spotify_display_name") or "your Spotify account",
        "time_range": time_range,
    })


if __name__ == "__main__":
    app.run(debug=True)
