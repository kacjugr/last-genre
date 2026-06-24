#!/usr/bin/env python3
"""Web app for exploring a Last.fm user's top artists and genre recommendations."""

import os
from collections import Counter

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from lastfm import GeminiBusyError, PERIOD_CHOICES, ask_gemini_with_retry, build_gemini_prompt, get_top_artists, get_top_tags

load_dotenv()

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    form = {
        "username": "",
        "limit": 10,
        "period": "overall",
        "genre": "",
    }
    error = None
    artists = None
    tag_counts = None

    if request.method == "POST":
        form["username"] = request.form.get("username", "").strip()
        form["period"] = request.form.get("period", "overall")
        form["genre"] = request.form.get("genre", "").strip()

        try:
            form["limit"] = int(request.form.get("limit", 10))
        except ValueError:
            form["limit"] = 10

        if not form["username"]:
            error = "Please enter a Last.fm username."
        elif form["period"] not in PERIOD_CHOICES:
            error = "Invalid period selected."
        else:
            api_key = os.environ.get("LASTFM_API_KEY")
            if not api_key:
                error = "Server is missing the LASTFM_API_KEY environment variable."
            else:
                try:
                    artists = get_top_artists(form["username"], api_key, form["limit"], form["period"])
                except (requests.RequestException, RuntimeError) as e:
                    error = f"Could not fetch top artists: {e}"
                    artists = None

        if artists is not None:
            if not artists:
                error = f"No top artists found for user '{form['username']}'."
            else:
                counts: Counter = Counter()
                for artist in artists:
                    try:
                        counts.update(get_top_tags(artist["name"], api_key))
                    except (requests.RequestException, RuntimeError):
                        pass
                tag_counts = counts.most_common()

    return render_template(
        "index.html",
        period_choices=PERIOD_CHOICES,
        form=form,
        error=error,
        artists=artists,
        tag_counts=tag_counts,
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
    try:
        reply, retries, used_fallback = ask_gemini_with_retry(prompt, gemini_api_key)
    except GeminiBusyError as e:
        return jsonify({"busy": True, "retries": e.retries, "fallback": e.tried_fallback})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"reply": reply, "retries": retries, "fallback": used_fallback})


if __name__ == "__main__":
    app.run(debug=True)
