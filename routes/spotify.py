"""Every /spotify/* route, plus the OAuth plumbing behind it, isolated in a Flask
Blueprint so app.py — and the /lastfm/* and other basic routes living there — never
need to import spotify.py or know how Spotify's OAuth flow works. get_connection_status()
is registered into registered_services["spotify"]["get_conn_status"] rather than
imported by name — see services/registry.py for why this key is optional per service.
"""

import os
import secrets

import requests
import spotipy
from flask import Blueprint, jsonify, redirect, request, session, url_for

from services.registry import registered_services
from services.spotify_service import get_top_artists
from spotify import (
    TOKEN_SESSION_KEY,
    get_client,
    get_client_credentials_client,
    get_current_user,
    get_recommendation_artwork,
    is_connected,
    make_oauth,
)

spotify_bp = Blueprint("spotify", __name__, url_prefix="/spotify")


def _redirect_uri() -> str:
    return os.environ.get("SPOTIFY_REDIRECT_URI", request.url_root.rstrip("/") + "/spotify/callback")


def _oauth():
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    return make_oauth(session, client_id, client_secret, _redirect_uri())


def get_connection_status() -> dict:
    oauth = _oauth()
    return {
        "connected": bool(oauth and is_connected(oauth)),
        "display_name": session.get("spotify_display_name") or "",
        "error": request.args.get("spotify_error"),  # set via the ?spotify_error= redirect from /callback
    }


registered_services["spotify"]["get_conn_status"] = get_connection_status


@spotify_bp.route("/login", methods=["GET"])
def login():
    oauth = _oauth()
    if not oauth:
        return jsonify({"error": "Server is missing Spotify API credentials."}), 500

    state = secrets.token_urlsafe(16)
    session["spotify_state"] = state
    return redirect(oauth.get_authorize_url(state=state))


@spotify_bp.route("/logout", methods=["GET"])
def logout():
    session.pop(TOKEN_SESSION_KEY, None)
    session.pop("spotify_display_name", None)
    return redirect(url_for("index"))


@spotify_bp.route("/callback", methods=["GET"])
def callback():
    error = request.args.get("error")
    if error:
        return redirect(url_for("index", spotify_error=f"Spotify authorization failed: {error}"))

    state = request.args.get("state")
    if not state or state != session.pop("spotify_state", None):
        return redirect(url_for("index", spotify_error="Spotify login state mismatch. Please try again."))

    oauth = _oauth()
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
        user = get_current_user(get_client(oauth))
        session["spotify_display_name"] = (user.get("display_name") or user.get("id")) if user else None
    except (spotipy.SpotifyException, requests.RequestException):
        session["spotify_display_name"] = None

    return redirect(url_for("index"))


@spotify_bp.route("/top-artists", methods=["POST"])
def top_artists():
    data = request.get_json(silent=True) or {}
    context = {
        "spotify_oauth": _oauth(),
        "spotify_display_name": session.get("spotify_display_name") or "your Spotify account",
    }
    body, status = get_top_artists(data, context)
    return jsonify(body), status


@spotify_bp.route("/artwork", methods=["POST"])
def artwork():
    data = request.get_json(silent=True) or {}
    recommendations = data.get("recommendations") or []

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return jsonify({"error": "Server is missing Spotify API credentials."}), 500

    sp = get_client_credentials_client(client_id, client_secret)
    result = get_recommendation_artwork(sp, recommendations)

    return jsonify({"artwork": result})
