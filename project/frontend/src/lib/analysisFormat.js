export function clip(text, limit = 1024) {
  const value = text == null ? "" : String(text);
  return value.length <= limit ? value : `${value.slice(0, Math.max(0, limit - 3))}...`;
}

export function fmtList(lines, maxLines = 6) {
  if (!Array.isArray(lines) || lines.length === 0) return "（無）";

  const cleaned = lines.map((item) => String(item).trim()).filter(Boolean).slice(0, maxLines);
  if (cleaned.length === 0) return "（無）";

  return cleaned.map((line, index) => `${index + 1}. ${line}`).join("\n");
}

export function fmtKeywords(words, maxItems = 12) {
  if (!Array.isArray(words) || words.length === 0) return "（無）";

  const cleaned = words.map((item) => String(item).trim()).filter(Boolean).slice(0, maxItems);
  if (cleaned.length === 0) return "（無）";

  return cleaned.join("、");
}
