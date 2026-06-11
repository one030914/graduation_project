export function JobStatusPanel({ jobState }) {
  const actionLabels = {
    analyze: "綜合分析",
    summary: "摘要分析",
    keyword: "關鍵詞分析",
    topics: "熱門主題分析",
    emotion: "情緒風向分析",
    criticism: "批評回饋分析",
    timeline: "時間軸分析",
    videoContent: "影片內容脈絡分析",
  };

  const statusLabel = {
    submitting: "提交中",
    queued: "排隊中",
    running: "分析中",
    completed: jobState.fromCache ? "已完成（快取）" : "已完成",
    failed: "分析失敗",
  }[jobState.status] || `未知狀態：${jobState.status}`;

  const actionLabel = actionLabels[jobState.action] || "分析";

  const isRunning = jobState.status === "running";
  const toneClassName =
    jobState.status === "failed"
      ? "border-red-500/30 bg-red-950/30 text-red-100"
      : jobState.status === "completed"
        ? "border-emerald-400/30 bg-emerald-950/20 text-emerald-100"
        : "border-sky-400/20 bg-sky-950/20 text-sky-100";

  const badgeClassName =
    jobState.status === "failed"
      ? "bg-red-400/10 text-red-100 ring-red-300/20"
      : jobState.status === "completed"
        ? "bg-emerald-400/10 text-emerald-100 ring-emerald-300/20"
        : "bg-sky-400/10 text-sky-100 ring-sky-300/20";

  return (
    <section className={`relative overflow-hidden rounded-2xl border p-4 backdrop-blur-md ${toneClassName}`}>
      {isRunning && <div className="job-status-scan pointer-events-none absolute inset-0" />}

      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-base font-medium">{actionLabel}</p>
          <div className="mt-1 flex items-center gap-3">
            <p className="text-xl font-semibold">{statusLabel}</p>
            {isRunning && (
              <div className="flex items-center gap-1.5" aria-hidden="true">
                <span className="job-status-dot" />
                <span className="job-status-dot job-status-dot-delay-1" />
                <span className="job-status-dot job-status-dot-delay-2" />
              </div>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ring-1 ${badgeClassName}`}>
            {jobState.status}
          </span>
        </div>
      </div>

      {isRunning && (
        <div className="relative mt-4">
          <div className="h-2 overflow-hidden rounded-full bg-white/8 ring-1 ring-white/10">
            <div className="job-status-marquee h-full rounded-full" />
          </div>
          <p className="mt-2 text-sm text-white/60">
            任務正在背景執行，完成後會自動更新結果。
          </p>
        </div>
      )}

      {jobState.error && <p className="relative mt-3 text-base">{jobState.error}</p>}
    </section>
  );
}
