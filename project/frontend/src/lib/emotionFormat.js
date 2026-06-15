export const EMOTION_DEFINITIONS = [
  { key: "Neutral", label: "平淡" },
  { key: "Joy", label: "開心" },
  { key: "Angry", label: "憤怒" },
  { key: "Sad", label: "悲傷" },
  { key: "Surprised", label: "驚奇" },
  { key: "Disgusted", label: "厭惡" },
  { key: "Other", label: "其他" },
];

const EMOTION_LABELS = Object.fromEntries(
  EMOTION_DEFINITIONS.map((emotion) => [emotion.key, emotion.label]),
);
  
const EMOTION_ALIASES = new Map([
  ["joy", "Joy"],
  ["開心", "Joy"],
  ["開心語調", "Joy"],
  ["喜悅", "Joy"],
  ["喜悅/支持", "Joy"],
  ["喜悅/稱讚", "Joy"],
  ["angry", "Angry"],
  ["憤怒", "Angry"],
  ["憤怒語調", "Angry"],
  ["憤怒/不滿", "Angry"],
  ["sad", "Sad"],
  ["悲傷", "Sad"],
  ["悲傷語調", "Sad"],
  ["悲傷/遺憾", "Sad"],
  ["surprised", "Surprised"],
  ["驚奇", "Surprised"],
  ["驚奇語調", "Surprised"],
  ["驚訝", "Surprised"],
  ["disgusted", "Disgusted"],
  ["厭惡", "Disgusted"],
  ["厭惡語調", "Disgusted"],
  ["反感", "Disgusted"],
  ["反感/強烈不滿", "Disgusted"],
  ["neutral", "Neutral"],
  ["平淡", "Neutral"],
  ["平淡語氣", "Neutral"],
  ["中性", "Neutral"],
  ["other", "Other"],
  ["others", "Other"],
  ["其他", "Other"],
  ["其他/無法對齊", "Other"],
  ["其他/無法判定", "Other"],
  ["未分類", "Other"],
  ["無法判定", "Other"],
]);

export function normalizeEmotionKey(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return EMOTION_ALIASES.get(normalized) || null;
}

export function getEmotionLabel(value) {
  const key = normalizeEmotionKey(value);
  return (key && EMOTION_LABELS[key]) || String(value || "").trim() || "未知";
}
