/*
 * Central registries for the self-registering plugin pattern used by the
 * per-service modules in this directory (lastfm.js, spotify.js, ...).
 *
 * Each registry maps a service key ('lastfm', 'spotify', ...) to a function
 * with a shared, service-agnostic signature that index.html calls without
 * knowing which service it's talking to:
 *
 *   formValueGetters[service]()          -> reads that service's form fields,
 *                                            returns a plain object
 *   fetchTopArtistsFns[service](limit, v) -> Promise<data> from that service's
 *                                            top-artists endpoint
 *   cacheKeyBuilders[service](v)         -> localStorage cache key string
 *
 * HOW TO ADD A NEW SERVICE
 *   1. Create static/js/<service>.js.
 *   2. Implement getFormValues(), fetchTopArtists(limit, v), and cacheKey(v)
 *      there, matching the signatures above.
 *   3. At the TOP LEVEL of that file — not inside a function, so it runs at
 *      module-load time — import the three registries below and assign your
 *      service's entry, e.g.:
 *        formValueGetters.myservice = getFormValues;
 *        fetchTopArtistsFns.myservice = fetchTopArtists;
 *        cacheKeyBuilders.myservice = cacheKey;
 *   4. In index.html, add a side-effect-only import of your new file so its
 *      registration code actually executes — index.html never builds these
 *      registries itself, only reads from them.
 *
 * HOW TO FIND EXISTING SELF-REGISTERING MODULES
 *   Search static/js/ for files importing this module — currently lastfm.js
 *   and spotify.js. Each carries a short comment at the top pointing back here.
 */

export var formValueGetters = {};
export var fetchTopArtistsFns = {};
export var cacheKeyBuilders = {};
