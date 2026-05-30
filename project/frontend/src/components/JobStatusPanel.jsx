const STAGE_LABELS = {
  collect: "抓取留言",
  emotion: "情緒分析",
  topics: "主題分析",
  summary: "摘要分析",
  keyword: "關鍵詞分析",
  criticism: "批評分析",
  timeline: "時間軸分析",
  video_content: "影片內容",
  synthesize: "AI 整合中",
};

export function JobStatusPanel({ jobState, onCancel }) {
  const actionLabels = {
    analyze: "綜合分析",
    summary: "摘要分析",
    keyword: "關鍵詞分析",
    topics: "主題分析",
    emotion: "情緒分析",
    criticism: "批評分析",
    timeline: "時間軸分析",
    videoContent: "影片內容",
  };

  const statusLabel = {
    submitting: "提交中",
    queued: "排隊中",
    running: "分析中",
    completed: jobState.fromCache ? "已完成（快取）" : "已完成",
    failed: "分析失敗",
    cancelled: "已停止",
  }[jobState.status] || `未知狀態：${jobState.status}`;

  const actionLabel = actionLabels[jobState.action] || "分析";
  const stageLabel = jobState.stage ? STAGE_LABELS[jobState.stage] || jobState.stage : null;
  const progressPercent = Math.round((jobState.stageProgress ?? 0) * 100);

  const isActive = ["submitting", "queued", "running"].includes(jobState.status);
  const isRunning = jobState.status === "running";
  const hasProgress = isRunning && (jobState.stageProgress ?? 0) > 0;

  const toneClassName =
    jobState.status === "failed"
      ? "border-red-500/30 bg-red-950/30 text-red-100"
      : jobState.status === "cancelled"
        ? "border-amber-400/30 bg-amber-950/20 text-amber-100"
        : jobState.status === "completed"
          ? "border-emerald-400/30 bg-emerald-950/20 text-emerald-100"
          : "border-sky-400/20 bg-sky-950/20 text-sky-100";

  const badgeClassName =
    jobState.status === "failed"
      ? "bg-red-400/10 text-red-100 ring-red-300/20"
      : jobState.status === "cancelled"
        ? "bg-amber-400/10 text-amber-100 ring-amber-300/20"
        : jobState.status === "completed"
          ? "bg-emerald-400/10 text-emerald-100 ring-emerald-300/20"
          : "bg-sky-400/10 text-sky-100 ring-sky-300/20";

  return (
    <section className={`relative overflow-hidden rounded-2xl border p-4 backdrop-blur-md ${toneClassName}`}>
      {isRunning && !hasProgress && <div className="job-status-scan pointer-events-none absolute inset-0" />}

      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium">{actionLabel}</p>
          <div className="mt-1 flex items-center gap-3">
            <p className="text-lg font-semibold">{statusLabel}</p>
            {isRunning && !hasProgress && (
              <div className="flex items-center gap-1.5" aria-hidden="true">
                <span className="job-status-dot" />
                <span className="job-status-dot job-status-dot-delay-1" />
                <span className="job-status-dot job-status-dot-delay-2" />
              </div>
            )}
          </div>
          {isRunning && stageLabel && (
            <p className="mt-1 text-sm text-white/70">
              目前步驟：{stageLabel}
              {hasProgress ? `（${progressPercent}%）` : ""}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ring-1 ${badgeClassName}`}>
            {jobState.status}
          </span>
          {isActive && jobState.jobId && (
            <button
              type="button"
              onClick={onCancel}
              className="inline-flex min-h-8 items-center rounded-full border border-red-300/25 bg-red-500/15 px-3 text-xs font-semibold text-red-100 transition hover:border-red-200/45 hover:bg-red-500/25 focus:outline-none focus:ring-2 focus:ring-red-300/50"
            >
              停止分析
            </button>
          )}
        </div>
      </div>

      {isRunning && (
        <div className="relative mt-4">
          <div className="h-2 overflow-hidden rounded-full bg-white/8 ring-1 ring-white/10">
            {hasProgress ? (
              <div
                className="h-full rounded-full bg-sky-400 transition-all duration-500 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            ) : (
              <div className="job-status-marquee h-full rounded-full" />
            )}
          </div>
          <p className="mt-2 text-xs text-white/60">
            {hasProgress
              ? "子分析完成後會逐步顯示在下方，無需等待全部完成。"
              : "任務正在背景執行，完成後會自動更新結果。"}
          </p>
        </div>
      )}

      {jobState.error && <p className="relative mt-3 text-sm">{jobState.error}</p>}
    </section>
  );
}
