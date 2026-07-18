export function spotifyCacheKey(timeRange) {
  return 'spotify_v1_' + timeRange.replace('_term', '');
}

export function fetchSpotifyTopArtists(limit, v) {
  return fetch('/fetch-spotify-artists', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ limit: limit, time_range: v.timeRange }),
  }).then(function (res) { return res.json(); });
}
