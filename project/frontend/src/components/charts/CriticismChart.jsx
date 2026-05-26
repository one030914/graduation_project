"use client";

function fmtPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

export function CriticismChart({ data = [] }) {
  const chartData = data
    .map((item) => ({
      label: item.label || item.key || "未知",
      count: Number(item.count ?? 0),
      value: Number(item.value ?? item.ratio ?? 0),
    }))
    .filter((item) => item.count > 0 || item.value > 0)
    .slice(0, 6);

  if (chartData.length === 0) return null;

  return (
    <section className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-7 text-white shadow-[0_22px_60px_rgba(2,6,23,0.36)] ring-1 ring-indigo-300/5 backdrop-blur-md">
      <h3 className="text-xl font-black tracking-normal">批評與改善訊號</h3>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {chartData.map((item, index) => {
          const width = Math.max(8, Math.min(100, item.value * 100));
          const tone = index === 0 ? "from-amber-400 to-orange-400" : "from-indigo-400 to-violet-400";

          return (
            <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.04] p-4 ring-1 ring-white/5">
              <div className="flex items-start justify-between gap-3">
                <p className="min-w-0 text-sm font-black text-white/72">{item.label}</p>
                <span className="rounded-full bg-white/8 px-2 py-1 text-xs font-black text-white/45">
                  {fmtPercent(item.value)}
                </span>
              </div>
              <p className="mt-4 text-3xl font-black text-white">{item.count}</p>
              <p className="mt-1 text-xs font-bold text-white/42">相關留言數</p>

              <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-800/80 ring-1 ring-white/5">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${tone} shadow-[0_0_18px_rgba(129,140,248,0.26)]`}
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
