"use client";

import { clip, fmtList } from "@/lib/analysisFormat";
import { InfoTile, ResultCard, ResultFooter, ResultShell } from "@/components/results/ResultCards";

export function SummaryResultView({ result }) {
  if (!result) return null;

  if (result.error) {
    return (
      <p className="rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-100">
        {result.error}
      </p>
    );
  }

  const summaryPoints = result.summary_points ?? [];
  const summaryZh = result.summary_zh ?? [];
  const summaryEn = result.summary_en ?? [];
  const langRatio = result.lang_ratio ?? null;

  return (
    <ResultShell label="Summary" title={`留言摘要：${clip(result.title || result.video_id, 256)}`}>
      <ResultCard title="分析狀態">
        <div className="grid gap-3 sm:grid-cols-3">
          <InfoTile label="狀態" value={result.status || "ok"} />
          <InfoTile label="分析留言數" value={result.analyzed_comments ?? 0} />
          <InfoTile label="總留言數" value={result.total_comments ?? 0} />
        </div>
        {result.message && <p className="mt-3 text-amber-200">{result.message}</p>}
      </ResultCard>

      {summaryPoints.length > 0 && (
        <ResultCard title="留言摘要">
          <p className="whitespace-pre-line">{fmtList(summaryPoints)}</p>
        </ResultCard>
      )}

      {summaryPoints.length === 0 && summaryZh.length > 0 && (
        <ResultCard title="中文摘要">
          <p className="whitespace-pre-line">{fmtList(summaryZh)}</p>
        </ResultCard>
      )}

      {summaryPoints.length === 0 && summaryEn.length > 0 && (
        <ResultCard title="English Summary">
          <p className="whitespace-pre-line">{fmtList(summaryEn)}</p>
        </ResultCard>
      )}

      {langRatio && (
        <ResultCard title="語言佔比">
          <div className="grid gap-3 sm:grid-cols-3">
            <InfoTile label="中文" value={`${((langRatio.zh ?? 0) * 100).toFixed(1)}%`} />
            <InfoTile label="英文" value={`${((langRatio.en ?? 0) * 100).toFixed(1)}%`} />
            <InfoTile label="其他" value={`${((langRatio.other ?? 0) * 100).toFixed(1)}%`} />
          </div>
        </ResultCard>
      )}

      <ResultFooter>Summary：根據留言內容抽取代表性摘要。</ResultFooter>
    </ResultShell>
  );
}
