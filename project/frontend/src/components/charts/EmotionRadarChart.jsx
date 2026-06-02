"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const EMOTIONS = [
  { key: "Joy", label: "喜悅" },
  { key: "Angry", label: "憤怒" },
  { key: "Sad", label: "悲傷" },
  { key: "Disgusted", label: "厭惡" },
  { key: "Surprised", label: "驚訝" },
  { key: "Fearful", label: "恐懼" },
  { key: "Neutral", label: "中性" },
];

const EMOTION_LABELS = Object.fromEntries(EMOTIONS.map((emotion) => [emotion.key, emotion.label]));
const EMOTION_KEYS = EMOTIONS.map((emotion) => emotion.key);

function normalizeEmotionKey(value) {
  const rawValue = String(value || "").trim();
  if (!rawValue) return null;

  const directKey = EMOTION_KEYS.find((key) => key.toLowerCase() === rawValue.toLowerCase());
  if (directKey) return directKey;

  return EMOTIONS.find((emotion) => emotion.label === rawValue)?.key || rawValue;
}

function normalizeRatio(value) {
  const ratio = Number(value || 0);
  if (!Number.isFinite(ratio) || ratio <= 0) return 0;
  return ratio > 1 ? ratio / 100 : ratio;
}

function normalizeCount(value) {
  const count = Number(value || 0);
  return Number.isFinite(count) && count > 0 ? count : 0;
}

function buildChartData(data) {
  const emotionMap = new Map(
    EMOTIONS.map((emotion) => [
      emotion.key,
      {
        key: emotion.key,
        name: emotion.label,
        count: 0,
        providedRatio: 0,
      },
    ]),
  );

  data.forEach((item, index) => {
    const rawName = item.key || item.label || item.emotion || item.name || `emotion-${index}`;
    const key = normalizeEmotionKey(rawName);
    if (!key) return;

    const existing = emotionMap.get(key) ?? {
      key,
      name: EMOTION_LABELS[key] || String(rawName),
      count: 0,
      providedRatio: 0,
    };

    emotionMap.set(key, {
      ...existing,
      count: existing.count + normalizeCount(item.count ?? item.total ?? item.value),
      providedRatio: Math.max(existing.providedRatio, normalizeRatio(item.ratio ?? item.percent)),
    });
  });

  const items = Array.from(emotionMap.values());
  const hasData = items.some((item) => item.count > 0 || item.providedRatio > 0);
  if (!hasData) return [];

  const totalCount = items.reduce((sum, item) => sum + item.count, 0);

  return items.map((item) => {
    const ratio = item.providedRatio > 0 ? item.providedRatio : item.count / Math.max(totalCount, 1);

    return {
      ...item,
      ratio,
      score: ratio * 100,
    };
  });
}

export function EmotionRadarChart({ data = [] }) {
  const chartData = buildChartData(data);
  if (chartData.length === 0) return null;

  const maxScore = Math.max(...chartData.map((item) => item.score), 1);
  const dominant = [...chartData].sort((a, b) => b.score - a.score)[0];

  return (
    <section className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-7 text-white shadow-[0_22px_60px_rgba(2,6,23,0.36)] ring-1 ring-indigo-300/5 backdrop-blur-md">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-black tracking-normal">情緒心理圖譜</h3>
          <p className="mt-2 text-sm font-semibold text-white/45">雷達圖呈現留言區情緒分布</p>
        </div>
        <div className="rounded-xl border border-indigo-300/10 bg-indigo-400/8 px-3 py-2 text-right">
          <p className="text-xs font-bold text-white/38">主導情緒</p>
          <p className="mt-1 text-sm font-black text-indigo-200">{dominant.name}</p>
        </div>
      </div>

      <div className="mt-5 h-80 min-h-80 min-w-0">
        <ResponsiveContainer width="100%" height={320} minWidth={0} minHeight={280}>
          <RadarChart data={chartData} outerRadius="72%">
            <PolarGrid gridType="polygon" stroke="rgba(148, 163, 184, 0.24)" />
            <PolarAngleAxis
              dataKey="name"
              tick={{ fill: "#cbd5e1", fontSize: 12, fontWeight: 800 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, maxScore]}
              tick={false}
              axisLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "#0f172a",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                borderRadius: 12,
                boxShadow: "0 18px 40px rgba(2, 6, 23, 0.32)",
                color: "#e2e8f0",
              }}
              formatter={(value, name, props) => {
                const payload = props?.payload ?? {};
                const ratio = `${((payload.ratio ?? 0) * 100).toFixed(1)}%`;
                return [`${payload.count ?? 0} 則 / ${ratio}`, "情緒聲量"];
              }}
              labelStyle={{ color: "#e2e8f0", fontWeight: 800 }}
            />
            <Radar
              dataKey="score"
              fill="#818cf8"
              fillOpacity={0.34}
              stroke="#a5b4fc"
              strokeWidth={3}
              dot={{ r: 4, fill: "#fbbf24", stroke: "#070d20", strokeWidth: 2 }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
