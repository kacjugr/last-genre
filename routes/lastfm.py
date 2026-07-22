"""Every /lastfm/* route, isolated in a Flask Blueprint so app.py never needs to
import lastfm.py directly — mirrors routes/spotify.py's structure. Artist tag
counts and chart top tags are just as Last.fm-specific as top-artists, so they
live under this same /lastfm/ prefix rather than leaving lastfm.py imports
behind in app.py.
"""

import json
import os
from collections import Counter

import requests
from flask import Blueprint, Response, jsonify, request, stream_with_context

from lastfm import get_artist_top_tags, get_chart_top_tags
from services.lastfm_service import get_top_artists

lastfm_bp = Blueprint("lastfm", __name__, url_prefix="/lastfm")


@lastfm_bp.route("/top-artists", methods=["POST"])
def top_artists():
    data = request.get_json(silent=True) or {}
    context = {"lastfm_api_key": os.environ.get("LASTFM_API_KEY")}
    body, status = get_top_artists(data, context)
    return jsonify(body), status


@lastfm_bp.route("/artist-tag-counts", methods=["POST"])
def artist_tag_counts():
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


@lastfm_bp.route("/chart-top-tags", methods=["GET"])
def chart_top_tags():
    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        return jsonify({"error": "Server is missing the LASTFM_API_KEY environment variable."}), 500

    try:
        tags = get_chart_top_tags(api_key)
    except (requests.RequestException, RuntimeError) as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"tags": tags})
