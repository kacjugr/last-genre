export function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// Gemini (and possibly other free-text sources) sometimes wraps emphasis in
// **double asterisks** (markdown-style bold). Escape first so the source text
// can't inject markup, then turn the (now-escaped, so still literal) asterisk
// pairs into real <strong> tags.
export function boldify(str) {
  return esc(str).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}
