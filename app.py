#!/usr/bin/env python3
"""Web app for exploring a Last.fm user's top artists and genre recommendations."""

import json
import os
import secrets
import time
from collections import Counter

import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request, session, stream_with_context, url_for

from gemini import ask_gemini_with_retry_streaming, build_gemini_prompt
from lastfm import PERIOD_CHOICES, get_artist_top_tags, get_chart_top_tags, get_user_top_artists
from spotify import (
    TIME_RANGE_CHOICES,
    build_authorize_url,
    exchange_code_for_token,
    get_current_user as get_spotify_current_user,
    get_user_top_artists as get_spotify_top_artists,
    refresh_access_token,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

LIMIT_CHOICES = [10, 25, 50, 100, 250, 500]


def _spotify_redirect_uri() -> str:
    return os.environ.get("SPOTIFY_REDIRECT_URI", request.url_root.rstrip("/") + "/spotify/callback")


@app.route("/", methods=["GET"])
def index():
    form = {
        "username": "kacjugr",
        "limit": 50,
        "period": "overall",
    }
    return render_template(
        "index.html",
        lastfm_period_choices=PERIOD_CHOICES,
        limit_choices=LIMIT_CHOICES,
        form=form,
        spotify_time_range_choices=TIME_RANGE_CHOICES,
        spotify_connected=bool(session.get("spotify_access_token")),
        spotify_error=request.args.get("spotify_error"),
    )


@app.route("/fetch-artists", methods=["POST"])
def fetch_artists():
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


@app.route("/fetch-tag-counts", methods=["POST"])
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


@app.route("/spotify/login", methods=["GET"])
def spotify_login():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    if not client_id:
        return jsonify({"error": "Server is missing the SPOTIFY_CLIENT_ID environment variable."}), 500

    state = secrets.token_urlsafe(16)
    session["spotify_state"] = state
    return redirect(build_authorize_url(client_id, _spotify_redirect_uri(), state))


@app.route("/spotify/logout", methods=["GET"])
def spotify_logout():
    session.pop("spotify_access_token", None)
    session.pop("spotify_refresh_token", None)
    session.pop("spotify_expires_at", None)
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

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return redirect(url_for("index", spotify_error="Server is missing Spotify API credentials."))

    code = request.args.get("code")
    if not code:
        return redirect(url_for("index", spotify_error="Spotify did not return an authorization code."))

    try:
        token_data = exchange_code_for_token(code, _spotify_redirect_uri(), client_id, client_secret)
    except requests.RequestException as e:
        return redirect(url_for("index", spotify_error=f"Could not connect to Spotify: {e}"))

    access_token = token_data["access_token"]
    session["spotify_access_token"] = access_token
    session["spotify_refresh_token"] = token_data.get("refresh_token")
    session["spotify_expires_at"] = time.time() + token_data["expires_in"]

    try:
        user = get_spotify_current_user(access_token)
        session["spotify_display_name"] = user.get("display_name") or user.get("id")
    except (requests.RequestException, RuntimeError):
        session["spotify_display_name"] = None

    return redirect(url_for("index"))


@app.route("/fetch-spotify-artists", methods=["POST"])
def fetch_spotify_artists():
    data = request.get_json(silent=True) or {}
    time_range = data.get("time_range", "long_term")
    try:
        limit = int(data.get("limit", 50))
    except (ValueError, TypeError):
        limit = 50

    if time_range not in TIME_RANGE_CHOICES:
        return jsonify({"error": "Invalid time range selected."}), 400

    access_token = session.get("spotify_access_token")
    if not access_token:
        return jsonify({"error": "Not connected to Spotify.", "needs_auth": True}), 401

    if session.get("spotify_expires_at", 0) <= time.time():
        refresh_token = session.get("spotify_refresh_token")
        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        if not refresh_token or not client_id or not client_secret:
            session.pop("spotify_access_token", None)
            return jsonify({"error": "Spotify session expired. Please reconnect.", "needs_auth": True}), 401
        try:
            token_data = refresh_access_token(refresh_token, client_id, client_secret)
        except requests.RequestException as e:
            return jsonify({"error": f"Could not refresh Spotify token: {e}"}), 500
        access_token = token_data["access_token"]
        session["spotify_access_token"] = access_token
        session["spotify_expires_at"] = time.time() + token_data["expires_in"]
        if token_data.get("refresh_token"):
            session["spotify_refresh_token"] = token_data["refresh_token"]

    try:
        artists = get_spotify_top_artists(access_token, limit, time_range)
    except (requests.RequestException, RuntimeError) as e:
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
