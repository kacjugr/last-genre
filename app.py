#!/usr/bin/env python3
"""Web app for exploring a Last.fm user's top artists and genre recommendations."""

import json
import os
from collections import Counter

import requests
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from gemini import ask_gemini_with_retry_streaming, build_gemini_prompt
from lastfm import PERIOD_CHOICES, get_artist_top_tags, get_chart_top_tags, get_user_top_artists

load_dotenv()

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    form = {
        "username": "kacjugr",
        "limit": 50,
        "period": "overall",
    }
    return render_template("index.html", period_choices=PERIOD_CHOICES, form=form)


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

    counts: Counter = Counter()
    for artist in artists:
        try:
            counts.update(get_artist_top_tags(artist["name"], api_key))
        except (requests.RequestException, RuntimeError):
            pass

    return jsonify({"artists": artists, "tag_counts": counts.most_common()})


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


if __name__ == "__main__":
    app.run(debug=True)
