"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function getHighlightLabel(index) {
  if (index === 0) return "最高討論高峰";
  if (index === 1) return "次高關注點";
  return "延伸討論點";
}

export function TimelineLineChart({ data = [], hotspot = null }) {
  const chartData = data
    .map((item) => ({
      time: item.time_label || String(item.seconds ?? ""),
      seconds: Number(item.seconds ?? 0),
      count: Number(item.count ?? 0),
      ratio: Number(item.ratio ?? 0),
    }))
    .filter((item) => item.count > 0)
    .sort((a, b) => a.seconds - b.seconds);

  if (chartData.length === 0) return null;

  const highlights = [...chartData]
    .sort((a, b) => b.count - a.count)
    .slice(0, 3)
    .map((item, index) => ({ ...item, label: getHighlightLabel(index) }))
    .sort((a, b) => a.seconds - b.seconds);
  const peak = highlights.reduce((best, item) => (item.count > best.count ? item : best), highlights[0]);

  return (
    <section className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-7 text-white shadow-[0_22px_60px_rgba(2,6,23,0.36)] ring-1 ring-indigo-300/5 backdrop-blur-md">
      <h3 className="text-xl font-black tracking-normal">留言時間軸熱點</h3>

      <div className="mt-6 h-72 min-h-72 min-w-0">
        <ResponsiveContainer width="100%" height={280} minWidth={0} minHeight={240}>
          <AreaChart data={chartData} margin={{ top: 16, right: 16, left: -18, bottom: 0 }}>
            <defs>
              <linearGradient id="timelineCountFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#818cf8" stopOpacity="0.34" />
                <stop offset="88%" stopColor="#818cf8" stopOpacity="0.02" />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#334155" vertical={false} opacity={0.48} />
            <XAxis
              dataKey="time"
              tick={{ fill: "#94a3b8", fontSize: 12, fontWeight: 700 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
            />
            <YAxis hide allowDecimals={false} />
            <Tooltip
              cursor={{ stroke: "rgba(129, 140, 248, 0.28)", strokeWidth: 2 }}
              contentStyle={{
                background: "#0f172a",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                borderRadius: 12,
                boxShadow: "0 18px 40px rgba(2, 6, 23, 0.32)",
                color: "#e2e8f0",
              }}
              formatter={(value, name) => {
                if (name === "count") return [value, "提及次數"];
                return [value, name];
              }}
              labelStyle={{ color: "#e2e8f0", fontWeight: 800 }}
            />
            <Area
              type="monotone"
              dataKey="count"
              fill="url(#timelineCountFill)"
              stroke="#818cf8"
              strokeWidth={4}
              dot={{ r: 5, fill: "#818cf8", stroke: "#070d20", strokeWidth: 2 }}
              activeDot={{ r: 7, fill: "#a5b4fc", stroke: "#ffffff", strokeWidth: 3 }}
            />
            {peak && (
              <ReferenceDot
                x={peak.time}
                y={peak.count}
                r={7}
                fill="#f59e0b"
                stroke="#070d20"
                strokeWidth={3}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {hotspot && (
        <div className="mt-6 rounded-xl border border-amber-300/15 bg-amber-400/8 px-4 py-3 text-sm font-semibold text-white/68 ring-1 ring-amber-300/10">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-amber-400/14 px-2.5 py-1 text-xs font-black text-amber-200">
              最高討論片段
            </span>
            <span className="font-black text-white">{hotspot.time_label}</span>
            <span className="text-white/45">提及 {hotspot.count ?? 0} 次</span>
          </div>
          {hotspot.representative_comment && (
            <p className="mt-2 line-clamp-2 text-white/58">{hotspot.representative_comment}</p>
          )}
        </div>
      )}

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {highlights.map((item, index) => {
          const color = index === 0 ? "amber" : index === 1 ? "indigo" : "rose";
          const colorClass = {
            amber: "bg-amber-400/10 text-amber-200 ring-amber-300/20",
            indigo: "bg-indigo-400/10 text-indigo-200 ring-indigo-300/20",
            rose: "bg-rose-400/10 text-rose-200 ring-rose-300/20",
          }[color];

          return (
            <div
              key={`${item.time}-${item.count}-${index}`}
              className={`rounded-xl px-4 py-3 text-center ring-1 ${colorClass}`}
            >
              <p className="text-sm font-black">{item.time}</p>
              <p className="mt-1 text-xs font-bold text-white/48">{item.label}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
