#!/usr/bin/env python3
"""Web app for exploring a Last.fm user's top artists and genre recommendations."""

import json
import os
import secrets

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from gemini import ask_gemini_with_retry_streaming, build_gemini_prompt
from routes.lastfm import lastfm_bp
from routes.spotify import spotify_bp
from services.registry import registered_services

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.register_blueprint(lastfm_bp)
app.register_blueprint(spotify_bp)


@app.route("/", methods=["GET"])
def index():
    # period_choices genuinely differs per service, so index.html loops over all of
    # them. limit_choices doesn't, so we just take it from the first registered service.
    period_choices = {service: info["period_choices"] for service, info in registered_services.items()}
    limit_choices = next(iter(registered_services.values()))["limit_choices"]

    # Only services with OAuth capabilites register a get_conn_status (see services/registry.py) 
    # Services without the OAuth concept won't appear here.
    conn_statuses = {
        service: info["get_conn_status"]()
        for service, info in registered_services.items()
        if "get_conn_status" in info
    }

    return render_template(
        "index.html",
        period_choices=period_choices,
        limit_choices=limit_choices,
        conn_statuses=conn_statuses,
    )


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
