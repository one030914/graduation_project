"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const BAR_COLORS = ["#fbbf24", "#818cf8", "#38bdf8", "#34d399"];

function clipLabel(label, limit = 9) {
  const value = String(label || "");
  return value.length > limit ? `${value.slice(0, Math.max(0, limit - 1))}…` : value;
}

function yAxisWidthFor(data, compact) {
  if (!compact) return 150;

  const longest = data.reduce((max, item) => Math.max(max, String(item.name || "").length), 0);
  return Math.min(158, Math.max(104, longest * 15 + 20));
}

function normalizeRatio(value) {
  const ratio = Number(value ?? 0);
  if (ratio > 1) return ratio / 100;
  return ratio;
}

function KeywordTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;

  const item = payload[0]?.payload ?? {};
  const ratio = item.ratio > 0 ? `${(item.ratio * 100).toFixed(1)}%` : "未提供比例";

  return (
    <div className="rounded-xl border border-white/12 bg-slate-900/95 px-4 py-3 text-slate-100 shadow-[0_18px_40px_rgba(2,6,23,0.36)] ring-1 ring-indigo-300/10 backdrop-blur-md">
      <p className="text-base font-black text-white">關鍵詞：{item.name}</p>
      <p className="mt-2 text-base font-semibold text-indigo-200">
        出現次數：{item.count ?? 0} 則 / {ratio}
      </p>
    </div>
  );
}

export function KeywordBarChart({ data = [], compact = false }) {
  const chartData = data
    .map((item, index) => ({
      name: item.keyword || item.label || item.name || `Keyword ${index + 1}`,
      count: Number(item.count ?? item.value ?? 0),
      ratio: normalizeRatio(item.ratio),
    }))
    .filter((item) => item.count > 0)
    .slice(0, 10);

  if (chartData.length === 0) return null;

  const topKeyword = chartData[0];
  const totalCount = chartData.reduce((sum, item) => sum + item.count, 0);
  const yAxisWidth = yAxisWidthFor(chartData, compact);

  return (
    <section className={`${compact ? "h-full" : ""} rounded-2xl border border-white/10 bg-[#070d20]/90 p-7 text-white shadow-[0_22px_60px_rgba(2,6,23,0.36)] ring-1 ring-indigo-300/5 backdrop-blur-md`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-black tracking-normal text-indigo-200">熱門關鍵詞</h3>
          <p className="mt-2 text-base font-semibold text-white/45">留言中反覆出現的代表詞彙</p>
        </div>
      </div>

      <div className={`${compact ? "mt-5 h-[340px] min-h-[340px]" : "mt-6 h-[400px] min-h-[400px]"} min-w-0`}>
        <ResponsiveContainer width="100%" height={compact ? 340 : 400} minWidth={0} minHeight={compact ? 320 : 360}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 8, right: compact ? 16 : 32, left: compact ? 0 : 34, bottom: 10 }}
            barCategoryGap={compact ? 9 : 12}
          >
            <CartesianGrid stroke="#334155" horizontal={false} opacity={0.42} />
            <XAxis
              type="number"
              allowDecimals={false}
              tick={{ fill: "#aebbd0", fontSize: 18, fontWeight: 800 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={yAxisWidth}
              interval={0}
              tick={{ fill: "#e2e8f0", fontSize: compact ? 22 : 22, fontWeight: 900 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => clipLabel(value, compact ? 8 : 14)}
            />
            <Tooltip
              cursor={{ fill: "rgba(129, 140, 248, 0.08)" }}
              content={<KeywordTooltip />}
              wrapperStyle={{ outline: "none" }}
            />
            <Bar dataKey="count" radius={[0, 10, 10, 0]}>
              {chartData.map((item, index) => (
                <Cell key={item.name} fill={BAR_COLORS[index % BAR_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className={`${compact ? "mt-4 grid-cols-2" : "mt-5 grid-cols-2 sm:grid-cols-2"} grid gap-3`}>
        <div className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3">
          <p className="text-sm font-bold text-white/42">總出現次數</p>
          <p className="mt-1 text-xl font-black text-white">{totalCount}</p>
        </div>
        <div className="rounded-xl border border-indigo-300/15 bg-indigo-400/8 px-4 py-3">
          <p className="text-sm font-bold text-white/42">Top 佔比</p>
          <p className="mt-1 text-xl font-black text-indigo-200">
            {topKeyword.ratio > 0 ? `${(topKeyword.ratio * 100).toFixed(1)}%` : "--"}
          </p>
        </div>
      </div>
    </section>
  );
}
