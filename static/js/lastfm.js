// Self-registers into the shared service registries — see registries.js for
// the registration contract and how to add another service.
import { formValueGetters, fetchTopArtistsFns, cacheKeyBuilders } from "./registries.js";

export function getFormValues() {
  return {
    username: document.getElementById('username').value.trim(),
    period: document.getElementById('period').value,
  };
}

export function fetchTopArtists(limit, v) {
  return fetch('/fetch-artists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: v.username, period: v.period, limit: limit }),
  }).then(function (res) { return res.json(); });
}

export function cacheKey(v) {
  return 'lastfm_v1_' + v.username + '_' + v.period;
}

formValueGetters.lastfm = getFormValues;
fetchTopArtistsFns.lastfm = fetchTopArtists;
cacheKeyBuilders.lastfm = cacheKey;
