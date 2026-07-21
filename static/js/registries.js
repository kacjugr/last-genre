/*
 * Central registry for the self-registering plugin pattern used by the
 * per-service modules in this directory (lastfm.js, spotify.js, ...).
 *
 * registeredServices maps a service key ('lastfm', 'spotify', ...) to an object
 * of that service's own functions, under their natural names — index.html calls
 * these without knowing which service it's talking to:
 *
 *   registeredServices[service].getFormValues()          -> reads that service's
 *                                                            form fields, returns
 *                                                            a plain object
 *   registeredServices[service].fetchTopArtists(limit, v) -> Promise<data> from
 *                                                            that service's
 *                                                            top-artists endpoint
 *   registeredServices[service].cacheKey(v)               -> localStorage cache
 *                                                            key string
 *
 * Object.keys(registeredServices) gives the list of every service key that has
 * self-registered (in registration order), e.g. ['lastfm', 'spotify'] — how
 * index.html picks a default service dynamically without hardcoding any
 * particular one's name.
 *
 * HOW TO ADD A NEW SERVICE
 *   1. Create static/js/<service>.js.
 *   2. Implement getFormValues(), fetchTopArtists(limit, v), and cacheKey(v)
 *      there, matching the signatures above.
 *   3. At the TOP LEVEL of that file — not inside a function, so it runs at
 *      module-load time — import registeredServices and register an object of
 *      your three functions under your service's key:
 *        var callables = {};
 *        callables.getFormValues = getFormValues;
 *        callables.fetchTopArtists = fetchTopArtists;
 *        callables.cacheKey = cacheKey;
 *        registeredServices.myservice = callables;
 *   4. In index.html, add a side-effect-only import of your new file so its
 *      registration code actually executes — index.html never builds this
 *      registry itself, only reads from it.
 *
 * HOW TO FIND EXISTING SELF-REGISTERING MODULES
 *   Search static/js/ for files importing this module — currently lastfm.js
 *   and spotify.js. Each carries a short comment at the top pointing back here.
 */

export var registeredServices = {};
