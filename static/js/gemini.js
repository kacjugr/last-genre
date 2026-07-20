// Gemini replies end with a fenced ```json ... ``` block; split it from the prose above it.
export function splitGeminiReply(text) {
  var match = text.match(/```json\n([\s\S]*?)\n```\s*$/);
  if (!match) return { text: text.trim(), json: null };
  var plainText = text.slice(0, match.index).trim();
  var json = null;
  try { json = JSON.parse(match[1]); } catch (e) {}
  return { text: plainText, json: json };
}

// Streams recommendations for `genre` given a user's `artists`, calling onEvent(ev) for
// each progress/result event as it arrives (types: trying, waiting, trying_fallback,
// done, busy, error — see gemini.py's ask_gemini_with_retry_streaming). Returns a
// Promise that resolves once the stream ends, so the caller can still catch network
// errors the same way it would with a plain fetch.
export function fetchGeminiRecommendation(genre, artists, onEvent) {
  return fetch('/gemini', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ genre: genre, artists: artists }),
  }).then(function (res) {
    var reader = res.body.getReader();
    var decoder = new TextDecoder();
    var buffer = '';

    function read() {
      return reader.read().then(function (chunk) {
        if (chunk.done) return;
        buffer += decoder.decode(chunk.value, { stream: true });
        var lines = buffer.split('\n');
        buffer = lines.pop();
        lines.forEach(function (line) {
          if (line.slice(0, 6) === 'data: ') {
            try { onEvent(JSON.parse(line.slice(6))); } catch (e) {}
          }
        });
        return read();
      });
    }
    return read();
  });
}
