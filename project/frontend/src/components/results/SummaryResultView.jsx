"use client";

import { clip, fmtList } from "@/lib/analysisFormat";

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
    <article className="rounded-2xl border border-white/15 bg-gray-900/50 p-6 shadow-inner backdrop-blur-md">
      <h2 className="text-xl font-bold">留言摘要：{clip(result.title || result.video_id, 256)}</h2>

      <div className="mt-6 space-y-5">
        <section>
          <h3 className="font-semibold text-indigo-200">分析狀態</h3>
          <p className="mt-2 text-white/90">
            {result.status || "ok"} ｜ 分析留言數：{result.analyzed_comments ?? 0} /{" "}
            {result.total_comments ?? 0}
          </p>
          {result.message && <p className="mt-2 text-sm text-amber-200">{result.message}</p>}
        </section>

        {summaryPoints.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">留言摘要</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(summaryPoints)}</p>
          </section>
        )}

        {summaryPoints.length === 0 && summaryZh.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">中文摘要</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(summaryZh)}</p>
          </section>
        )}

        {summaryPoints.length === 0 && summaryEn.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">English Summary</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(summaryEn)}</p>
          </section>
        )}

        {langRatio && (
          <section>
            <h3 className="font-semibold text-indigo-200">語言佔比</h3>
            <p className="mt-2 text-white/90">
              中文：{((langRatio.zh ?? 0) * 100).toFixed(1)}% ｜ 英文：
              {((langRatio.en ?? 0) * 100).toFixed(1)}% ｜ 其他：
              {((langRatio.other ?? 0) * 100).toFixed(1)}%
            </p>
          </section>
        )}

        <footer className="border-t border-white/10 pt-4 text-sm text-white/50">
          Summary：根據留言內容抽取代表性摘要。
        </footer>
      </div>
    </article>
  );
}
