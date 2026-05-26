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

const EMOTION_LABELS = {
  Joy: "喜悅",
  Angry: "憤怒",
  Sad: "悲傷",
  Disgusted: "厭惡",
  Surprised: "驚訝",
  Fearful: "恐懼",
  Neutral: "中性",
};

export function EmotionBarChart({ data = [] }) {
  const rawChartData = data
    .map((item, index) => {
      const rawName = item.label || item.emotion || item.name || `emotion-${index}`;
      const count = Number(item.count ?? item.value ?? 0);
      const rawRatio = Number(item.ratio ?? item.percent ?? 0);
      const providedRatio = rawRatio > 1 ? rawRatio / 100 : rawRatio;

      return {
        name: EMOTION_LABELS[rawName] || rawName,
        count,
        providedRatio,
      };
    })
    .filter((item) => item.count > 0 || item.providedRatio > 0);

  const totalCount = rawChartData.reduce((sum, item) => sum + item.count, 0);
  const chartData = rawChartData.map((item) => {
    const ratio = item.providedRatio > 0 ? item.providedRatio : item.count / Math.max(totalCount, 1);

    return {
      ...item,
      ratio,
      score: ratio * 100,
    };
  });

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
