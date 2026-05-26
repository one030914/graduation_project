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
      <p className="text-sm font-black text-white">關鍵詞：{item.name}</p>
      <p className="mt-2 text-sm font-semibold text-indigo-200">
        出現次數：{item.count ?? 0} 則 / {ratio}
      </p>
    </div>
  );
}

export function KeywordBarChart({ data = [] }) {
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

  return (
    <section className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-7 text-white shadow-[0_22px_60px_rgba(2,6,23,0.36)] ring-1 ring-indigo-300/5 backdrop-blur-md">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-black tracking-normal">熱門關鍵詞</h3>
          <p className="mt-2 text-sm font-semibold text-white/45">留言中反覆出現的代表詞彙</p>
        </div>
        <div className="rounded-xl border border-amber-300/15 bg-amber-400/8 px-3 py-2 text-right">
          <p className="text-xs font-bold text-white/38">最高頻</p>
          <p className="mt-1 max-w-28 truncate text-sm font-black text-amber-200">{topKeyword.name}</p>
        </div>
      </div>

      <div className="mt-6 h-[360px] min-h-[360px] min-w-0">
        <ResponsiveContainer width="100%" height={360} minWidth={0} minHeight={320}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 4, right: 28, left: 18, bottom: 4 }}
            barCategoryGap={12}
          >
            <CartesianGrid stroke="#334155" horizontal={false} opacity={0.42} />
            <XAxis
              type="number"
              allowDecimals={false}
              tick={{ fill: "#94a3b8", fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: "#334155" }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={92}
              tick={{ fill: "#cbd5e1", fontSize: 12, fontWeight: 800 }}
              tickLine={false}
              axisLine={false}
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

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3">
          <p className="text-xs font-bold text-white/42">關鍵詞數</p>
          <p className="mt-1 text-xl font-black text-white">{chartData.length}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3">
          <p className="text-xs font-bold text-white/42">總出現次數</p>
          <p className="mt-1 text-xl font-black text-white">{totalCount}</p>
        </div>
        <div className="rounded-xl border border-indigo-300/15 bg-indigo-400/8 px-4 py-3">
          <p className="text-xs font-bold text-white/42">Top 佔比</p>
          <p className="mt-1 text-xl font-black text-indigo-200">
            {topKeyword.ratio > 0 ? `${(topKeyword.ratio * 100).toFixed(1)}%` : "--"}
          </p>
        </div>
      </div>
    </section>
  );
}
