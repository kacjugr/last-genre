"""Central registry for the self-registering service-module pattern used by
services/lastfm_service.py and services/spotify_service.py — the backend
counterpart to static/js/registries.js on the frontend.

registered_services maps a service key ('lastfm', 'spotify', ...) to a dict of
that service's own data, all in one place — mirroring registries.js's
registeredServices[service] = { ...callables } shape:

    registered_services[service]["period_choices"] -> {"choices": list[str], "default": str}
        The selectable period/time-range values for that service, and which
        one is preselected, used to build index.html's shared 'period'
        <select> without that template needing to know any service's values.

    registered_services[service]["limit_choices"] -> {"choices": list[int], "default": int}
        The selectable "number of artists" values for that service. Not
        currently service-specific in the UI — index.html just reads one
        canonical service's entry to render a single shared radio group —
        but registered per-service for the same reason period_choices is:
        structural consistency, and in case a future service ever needs
        different choices. DEFAULT_LIMIT_CHOICES below is there so services
        that don't need their own distinct set can just reference it instead
        of repeating the literal.

    registered_services[service]["get_conn_status"]() -> dict  (OPTIONAL)
        Only present for services with something to actually check — an
        OAuth session, an API handshake, etc. Last.fm has no such concept
        (there's no login step, just a typed username), so it doesn't
        register this key at all, rather than supplying a stub that fakes a
        connection state it doesn't have. Callers should treat a missing key
        as "this service has nothing to report here," not as a bug — e.g.
        app.py's index() only calls get_conn_status() for services where the
        key exists, so lastfm is simply absent from the resulting dict.

HOW TO ADD A NEW SERVICE
  1. Create services/<service>_service.py.
  2. Implement get_top_artists(data, context) -> (body, status) there.
  3. At the top level of that file — not inside a function, so it runs at
     import time — import this module and register a dict of your service's
     entries:
       registered_services['<service>'] = {
           "period_choices": {"choices": YOUR_PERIOD_CHOICES, "default": YOUR_DEFAULT_CHOICE},
           "limit_choices": DEFAULT_LIMIT_CHOICES,  # or your own {"choices": ..., "default": ...}
       }
  4. In routes/<service>.py, import get_top_artists directly from
     services/<service>_service.py and call it — that import also triggers
     the registration side effect above.
"""

registered_services = {}

DEFAULT_LIMIT_CHOICES = {"choices": [10, 25, 50, 100, 250, 500], "default": 50}
