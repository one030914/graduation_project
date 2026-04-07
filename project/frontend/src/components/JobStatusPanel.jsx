export function JobStatusPanel({ jobState }) {
    const statusLabel = {
      submitting: "正在建立工作",
      queued: "已加入隊列，等待處理",
      running: "分析中",
      completed: jobState.fromCache ? "已完成（來自快取）" : "分析完成",
      failed: "分析失敗",
    }[jobState.status] || `狀態：${jobState.status}`;
  
    const actionLabel = jobState.action === "topics" ? "主題分析" : "分析";
    const isRunning = jobState.status === "running";
    const toneClassName =
      jobState.status === "failed"
        ? "border-red-500/30 bg-red-950/30 text-red-100"
        : jobState.status === "completed"
          ? "border-emerald-400/30 bg-emerald-950/20 text-emerald-100"
          : "border-sky-400/20 bg-sky-950/20 text-sky-100";
  
    return (
      <section className={`relative overflow-hidden rounded-2xl border p-4 backdrop-blur-md ${toneClassName}`}>
        {isRunning && <div className="job-status-scan pointer-events-none absolute inset-0" />}
  
        <div className="relative flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium">{actionLabel}</p>
            <div className="mt-1 flex items-center gap-3">
              <p className="text-lg font-semibold">{statusLabel}</p>
              {isRunning && (
                <div className="flex items-center gap-1.5" aria-hidden="true">
                  <span className="job-status-dot" />
                  <span className="job-status-dot job-status-dot-delay-1" />
                  <span className="job-status-dot job-status-dot-delay-2" />
                </div>
              )}
            </div>
          </div>
  
          <div className="shrink-0">
            <span
              className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ring-1 ${
                jobState.status === "failed"
                  ? "bg-red-400/10 text-red-100 ring-red-300/20"
                  : jobState.status === "completed"
                    ? "bg-emerald-400/10 text-emerald-100 ring-emerald-300/20"
                    : "bg-sky-400/10 text-sky-100 ring-sky-300/20"
              }`}
            >
              {jobState.status}
            </span>
          </div>
        </div>
  
        {isRunning && (
          <div className="relative mt-4">
            <div className="h-2 overflow-hidden rounded-full bg-white/8 ring-1 ring-white/10">
              <div className="job-status-marquee h-full rounded-full" />
            </div>
            <p className="mt-2 text-xs text-white/60">
              系統正在輪詢工作狀態並整理分析結果
            </p>
          </div>
        )}
  
        {jobState.error && <p className="relative mt-3 text-sm">{jobState.error}</p>}
      </section>
    );
  }