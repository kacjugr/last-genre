// Self-registers into the shared service registries — see registries.js for
// the registration contract and how to add another service.
import { formValueGetters, fetchTopArtistsFns, cacheKeyBuilders } from "./registries.js";

export function getFormValues() {
  // The connected account's display name isn't a form field — it's rendered into a
  // data attribute at page load (see index() in app.py / index.html's service-toggle
  // div), so it can be read synchronously here rather than only known after a fetch.
  return {
    username: document.getElementById('service-toggle').dataset.spotifyDisplayName || '',
    period: document.getElementById('time_range').value,
  };
}

export function fetchTopArtists(limit, v) {
  return fetch('/spotify/top-artists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ limit: limit, time_range: v.period }),
  }).then(function (res) { return res.json(); });
}

export function cacheKey(v) {
  return 'spotify_v1_' + v.username + '_' + v.period.replace('_term', '');
}

// Looks up artist/album artwork for a list of Gemini recommendations, in the same
// order. Not part of the self-registering service registries above — it's Spotify's
// own catalog search, called directly regardless of which service is selected for
// top-artists (a Last.fm user gets artwork too, no Spotify connection required).
export function fetchArtwork(recommendations) {
  return fetch('/spotify/artwork', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recommendations: recommendations }),
  }).then(function (res) { return res.json(); });
}

formValueGetters.spotify = getFormValues;
fetchTopArtistsFns.spotify = fetchTopArtists;
cacheKeyBuilders.spotify = cacheKey;
