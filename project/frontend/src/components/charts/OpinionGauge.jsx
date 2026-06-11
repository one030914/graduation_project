"use client";

const GAUGE_LEVEL_LABELS = ["負向", "中性", "正向"];

function getGaugeCopy(score) {
  if (score >= 80) return "高度正向";
  if (score >= 65) return "正向偏高";
  if (score >= 45) return "中性/意見分歧";
  if (score >= 30) return "負面偏高";
  return "高度負面";
}

function getGaugeTone(score) {
  if (score >= 80)
    return "stroke-emerald-300 text-emerald-200 drop-shadow-[0_0_14px_rgba(110,231,183,0.42)]";
  if (score >= 65)
    return "stroke-lime-400 text-lime-300 drop-shadow-[0_0_14px_rgba(163,230,53,0.38)]";
  if (score >= 45)
    return "stroke-amber-400 text-amber-300 drop-shadow-[0_0_14px_rgba(251,191,36,0.42)]";
  if (score >= 30)
    return "stroke-orange-400 text-orange-300 drop-shadow-[0_0_14px_rgba(251,146,60,0.4)]";
  return "stroke-rose-400 text-rose-300 drop-shadow-[0_0_14px_rgba(251,113,133,0.38)]";
}

function getGaugeSummary(score) {
  if (score >= 80) return "目前留言區高度正向，支持、認同與喜悅回饋是主要聲量。";
  if (score >= 65) return "目前留言區正向偏高，整體回饋較穩定且具支持傾向。";
  if (score >= 45) return "目前留言區情緒偏中性，正反意見都有一定討論度。";
  if (score >= 30) return "目前留言區負面偏高，建議優先檢視不滿與疑慮來源。";
  return "目前留言區高度負面，批評與不滿聲量明顯，需要優先處理。";
}

export function OpinionGauge({ score = 0 }) {
  const safeScore = Math.max(0, Math.min(100, Number(score) || 0));
  const labelText = getGaugeCopy(safeScore);
  const tone = getGaugeTone(safeScore);
  const summary = getGaugeSummary(safeScore);

  return (
    <section className="min-h-[390px] rounded-2xl border border-white/10 bg-[#070d20]/90 p-7 text-white shadow-[0_22px_60px_rgba(2,6,23,0.4)] ring-1 ring-indigo-300/5 backdrop-blur-md">
      <h3 className="text-2xl font-black tracking-normal">輿情溫度計</h3>

      <div className="mt-9 flex flex-col items-center">
        <div className="h-48 w-full max-w-[480px]">
          <svg className="h-full w-full overflow-visible" viewBox="0 0 260 154" aria-hidden="true">
            <path
              d="M 28 134 A 102 102 0 0 1 232 134"
              fill="none"
              stroke="rgb(51 65 85)"
              strokeLinecap="round"
              strokeWidth="20"
            />
            <path
              className={tone}
              d="M 28 134 A 102 102 0 0 1 232 134"
              fill="none"
              pathLength="100"
              strokeLinecap="round"
              strokeDasharray={`${safeScore} 100`}
              strokeWidth="20"
            />
          </svg>
        </div>

        <div className="-mt-14 max-w-full px-4 text-center">
          <p className="text-2xl font-black leading-tight tracking-normal sm:text-3xl">
            {labelText}
          </p>
          <p className="mt-1.5 text-base font-black text-white/48">{safeScore}% 好評率</p>
        </div>

        <div
          className="mt-10 grid w-full max-w-[560px] text-center text-sm font-black text-white/45 sm:text-base"
          style={{
            gridTemplateColumns: "repeat(" + GAUGE_LEVEL_LABELS.length + ", minmax(0, 1fr))",
          }}
        >
          {GAUGE_LEVEL_LABELS.map((levelLabel) => (
            <span key={levelLabel} className="break-words px-1">
              {levelLabel}
            </span>
          ))}
        </div>
      </div>

      <p className="mx-auto mt-10 max-w-md text-center text-lg font-semibold leading-8 text-white/58">
        {summary}
      </p>
    </section>
  );
}
