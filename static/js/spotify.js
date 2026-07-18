// Self-registers into the shared service registries — see registries.js for
// the registration contract and how to add another service.
import { formValueGetters, fetchTopArtistsFns, cacheKeyBuilders } from "./registries.js";

export function getFormValues() {
  return {
    timeRange: document.getElementById('time_range').value,
  };
}

export function fetchTopArtists(limit, v) {
  return fetch('/fetch-spotify-artists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ limit: limit, time_range: v.timeRange }),
  }).then(function (res) { return res.json(); });
}

export function cacheKey(v) {
  return 'spotify_v1_' + v.timeRange.replace('_term', '');
}

formValueGetters.spotify = getFormValues;
fetchTopArtistsFns.spotify = fetchTopArtists;
cacheKeyBuilders.spotify = cacheKey;
