export const EMOTION_DEFINITIONS = [
  { key: "Joy", label: "喜悅" },
  { key: "Angry", label: "不滿" },
  { key: "Sad", label: "悲傷" },
  { key: "Surprised", label: "驚訝" },
  { key: "Disgusted", label: "反感" },
  { key: "Neutral", label: "中性" },
];

const EMOTION_LABELS = Object.fromEntries(
  EMOTION_DEFINITIONS.map((emotion) => [emotion.key, emotion.label]),
);
  
const EMOTION_ALIASES = new Map([
  ["joy", "Joy"],
  ["喜悅", "Joy"],
  ["喜悅/支持", "Joy"],
  ["喜悅/稱讚", "Joy"],
  ["angry", "Angry"],
  ["憤怒", "Angry"],
  ["憤怒/不滿", "Angry"],
  ["sad", "Sad"],
  ["悲傷", "Sad"],
  ["悲傷/遺憾", "Sad"],
  ["surprised", "Surprised"],
  ["驚訝", "Surprised"],
  ["disgusted", "Disgusted"],
  ["厭惡", "Disgusted"],
  ["反感", "Disgusted"],
  ["反感/強烈不滿", "Disgusted"],
  ["neutral", "Neutral"],
  ["中性", "Neutral"],
]);

export function normalizeEmotionKey(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return EMOTION_ALIASES.get(normalized) || null;
}

export function getEmotionLabel(value) {
  const key = normalizeEmotionKey(value);
  return (key && EMOTION_LABELS[key]) || String(value || "").trim() || "未知";
}
