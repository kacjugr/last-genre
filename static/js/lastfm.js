export function lastfmCacheKey(username, period) {
  return 'lastgenre_v1_' + username + '_' + period;
}

export function fetchLastfmTopArtists(limit, v) {
  return fetch('/fetch-artists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: v.username, period: v.period, limit: limit }),
  }).then(function (res) { return res.json(); });
}
