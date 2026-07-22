// Self-registers into the shared service registry — see registries.js for
// the registration contract and how to add another service.
import { registeredServices } from "./registries.js";

export function getFormValues() {
  return {
    username: document.getElementById('username').value.trim(),
    period: document.getElementById('period').value,
  };
}

export function fetchTopArtists(limit, v) {
  return fetch('/lastfm/top-artists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: v.username, period: v.period, limit: limit }),
  }).then(function (res) { return res.json(); });
}

export function cacheKey(v) {
  // No username means there's nothing to have cached yet — let callers treat a
  // null key as "no cache entry" rather than special-casing Last.fm themselves.
  if (!v.username) return null;
  return 'lastfm_v1_' + v.username + '_' + v.period;
}

export function getServiceName() {
  return 'Last.fm';
}

var callables = {};
callables.getFormValues = getFormValues;
callables.fetchTopArtists = fetchTopArtists;
callables.cacheKey = cacheKey;
callables.getServiceName = getServiceName;
registeredServices.lastfm = callables;
