// Gemini replies end with a fenced ```json ... ``` block; split it from the prose above it.
export function splitGeminiReply(text) {
  var match = text.match(/```json\n([\s\S]*?)\n```\s*$/);
  if (!match) return { text: text.trim(), json: null };
  var plainText = text.slice(0, match.index).trim();
  var json = null;
  try { json = JSON.parse(match[1]); } catch (e) {}
  return { text: plainText, json: json };
}
