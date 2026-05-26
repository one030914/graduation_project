"use client";

function normalizeRatio(item) {
  const ratio = Number(item.ratio ?? item.value ?? 0);
  if (ratio > 1) return Math.min(100, ratio);
  if (ratio > 0) return Math.min(100, ratio * 100);
  return 0;
}

export function TopicsBarChart({ data = [] }) {
  const chartData = data
    .map((item, index) => ({
      name: item.label || item.topic_name || item.name || `Topic ${index + 1}`,
      count: Number(item.count ?? item.size ?? 0),
      ratio: normalizeRatio(item),
    }))
    .filter((item) => item.count > 0 || item.ratio > 0)
    .slice(0, 6);

  if (chartData.length === 0) return null;

  const maxCount = Math.max(...chartData.map((item) => item.count), 1);
  const featured = chartData.slice(0, 2);

  return (
    <section className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-7 text-white shadow-[0_22px_60px_rgba(2,6,23,0.36)] ring-1 ring-indigo-300/5 backdrop-blur-md">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-black tracking-normal">熱門討論焦點</h3>
          <p className="mt-2 text-sm font-semibold text-white/45">留言區最常被提到的主軸</p>
        </div>
        <span className="rounded-full bg-indigo-400/10 px-3 py-1 text-xs font-black text-indigo-200 ring-1 ring-indigo-300/15">
          Top {chartData.length}
        </span>
      </div>

      <div className="mt-7 space-y-5">
        {chartData.slice(0, 4).map((item, index) => {
          const percent = item.ratio || (item.count / maxCount) * 100;
          return (
            <div key={`${item.name}-${index}`}>
              <div className="mb-2 flex items-center justify-between gap-3 text-sm font-black">
                <span className="min-w-0 truncate text-white/88">{item.name}</span>
                <span className="shrink-0 text-white/45">{Math.round(percent)}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-800/80 ring-1 ring-white/5">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-indigo-400 to-violet-400 shadow-[0_0_22px_rgba(129,140,248,0.34)]"
                  style={{ width: `${Math.max(8, Math.min(100, percent))}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {featured.length > 0 && (
        <div className="mt-8 space-y-3">
          <h4 className="text-sm font-black text-indigo-200">代表主題群</h4>
          {featured.map((item, index) => (
            <div
              key={`${item.name}-featured-${index}`}
              className="flex items-center gap-3 rounded-xl border border-indigo-300/10 bg-indigo-400/8 px-4 py-3 text-sm text-white/72"
            >
              <span>
                {item.count > 0 ? `${item.count} 則留言` : `${Math.round(item.ratio)}% 佔比`}
              </span>
              <span className="min-w-0 truncate font-semibold">{item.name}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
