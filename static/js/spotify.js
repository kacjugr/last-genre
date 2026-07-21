// Self-registers into the shared service registry — see registries.js for
// the registration contract and how to add another service.
import { registeredServices } from "./registries.js";

export function getFormValues() {
  // index.html's updateServiceUI() fills the shared #username field with the
  // connected account's display name (read-only) whenever Spotify is selected, so
  // it can be read the same way as Last.fm's typed username.
  return {
    username: document.getElementById('username').value.trim(),
    period: document.getElementById('period').value,
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
// order. Not part of the self-registering service registry above — it's Spotify's
// own catalog search, called directly regardless of which service is selected for
// top-artists (a Last.fm user gets artwork too, no Spotify connection required).
export function fetchArtwork(recommendations) {
  return fetch('/spotify/artwork', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recommendations: recommendations }),
  }).then(function (res) { return res.json(); });
}

var callables = {};
callables.getFormValues = getFormValues;
callables.fetchTopArtists = fetchTopArtists;
callables.cacheKey = cacheKey;
registeredServices.spotify = callables;
