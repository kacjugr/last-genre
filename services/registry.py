"""Central registry for the self-registering service-module pattern used by
services/lastfm_service.py and services/spotify_service.py — the backend
counterpart to static/js/registries.js on the frontend.

Each registry maps a service key ('lastfm', 'spotify', ...) to something with a
shared, service-agnostic shape that app.py calls without importing lastfm.py /
spotify.py directly:

    top_artists_fns[service](data, context) -> (body, status_code)
        Validates the request, fetches that service's top artists, and shapes
        the JSON response — same contract regardless of which service it is.
        `context` is a small dict of whatever any service might need (an API
        key, an OAuth client, a display name) that only app.py can provide
        per-request; each service reads only the keys it cares about.

    period_choices[service] -> {"choices": list[str], "default": str}
        The selectable period/time-range values for that service, and which
        one is preselected, used to build index.html's shared 'period'
        <select> without that template needing to know any service's values.

HOW TO ADD A NEW SERVICE
  1. Create services/<service>_service.py.
  2. Implement get_top_artists(data, context) -> (body, status) there.
  3. At the top level of that file — not inside a function, so it runs at
     import time — import this module and register:
       top_artists_fns['<service>'] = get_top_artists
       period_choices['<service>'] = {"choices": YOUR_PERIOD_CHOICES, "default": YOUR_DEFAULT_CHOICE}
  4. Import services/<service>_service.py in app.py (for its side effect —
     app.py never builds these dicts itself, only reads from them).
"""

top_artists_fns = {}
period_choices = {}
