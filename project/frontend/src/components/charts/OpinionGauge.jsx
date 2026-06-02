"use client";

function getGaugeCopy(score, label) {
  if (label) return label;
  if (score >= 72) return "正面 / 支持度高";
  if (score >= 45) return "中性 / 意見分歧";
  return "負面 / 疑慮偏高";
}

function getGaugeTone(score) {
  if (score >= 72) return "stroke-emerald-400 text-emerald-300 drop-shadow-[0_0_14px_rgba(52,211,153,0.38)]";
  if (score >= 45) return "stroke-amber-400 text-amber-300 drop-shadow-[0_0_14px_rgba(251,191,36,0.42)]";
  return "stroke-rose-400 text-rose-300 drop-shadow-[0_0_14px_rgba(251,113,133,0.38)]";
}

export function OpinionGauge({ score = 0, label = "" }) {
  const safeScore = Math.max(0, Math.min(100, Number(score) || 0));
  const labelText = getGaugeCopy(safeScore, label);
  const tone = getGaugeTone(safeScore);
  const summary =
    safeScore >= 72
      ? "目前留言區正面回饋明顯，支持與認同是主要聲量。"
      : safeScore >= 45
        ? "目前留言區情緒偏穩，正反意見都有一定討論度。"
        : "目前留言區疑慮較多，建議優先檢視負面聲量來源。";

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
          <p className="text-2xl font-black leading-tight tracking-normal sm:text-3xl">{labelText}</p>
          <p className="mt-1.5 text-base font-black text-white/48">{safeScore}% 好評率</p>
        </div>

        <div className="mt-10 grid w-full max-w-[460px] grid-cols-3 text-center text-lg font-black text-white/45">
          <span>負面</span>
          <span>中性</span>
          <span>正向</span>
        </div>
      </div>

      <p className="mx-auto mt-10 max-w-md text-center text-lg font-semibold leading-8 text-white/58">
        {summary}
      </p>
    </section>
  );
}
