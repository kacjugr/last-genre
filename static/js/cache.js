export function cache_check() {
  return { name: 'hello world' };
}

export function saveCache(key, update) {
  try {
    var existing = loadCache(key) || { fetchedAt: Date.now() };
    for (var k in update) existing[k] = update[k];
    localStorage.setItem(key, JSON.stringify(existing));
  } catch (e) {}
}

export function loadCache(key) {
  try {
    var raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch (e) { return null; }
}

export function save_artist_tags_cache(artist_id, tags) {
  try {
    var existing = load_artist_tags_cache(artist_id) || { fetchedAt: Date.now() };
    existing.tags = tags;
    localStorage.setItem('artist_tags_' + artist_id, JSON.stringify(existing));
  } catch (e) {}
}

export function load_artist_tags_cache(artist_id) {
  try {
    var raw = localStorage.getItem('artist_tags_' + artist_id);
    return raw ? JSON.parse(raw) : null;
  } catch (e) { return null; }
}