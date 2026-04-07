"use client";

import { clip, fmtKeywords, fmtList } from "@/lib/analysisFormat";

export function AnalysisResultView({ result }) {
  if (!result) return null;

  if (result.error) {
    return (
      <p className="rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-100">
        {result.error}
      </p>
    );
  }

  return (
    <article className="rounded-2xl border border-white/15 bg-gray-900/50 p-6 shadow-inner backdrop-blur-md">
      <h2 className="text-xl font-bold">標題：{clip(result.title || result.video_id, 256)}</h2>

      <div className="mt-6 space-y-5">
        {result.summary_zh?.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">中文摘要</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(result.summary_zh)}</p>
          </section>
        )}

        {result.summary_en?.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">English summary</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(result.summary_en)}</p>
          </section>
        )}

        {result.keywords_zh?.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">中文關鍵字</h3>
            <p className="mt-2 text-white/90">{fmtKeywords(result.keywords_zh)}</p>
          </section>
        )}

        {result.keywords_en?.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">English keywords</h3>
            <p className="mt-2 text-white/90">{fmtKeywords(result.keywords_en)}</p>
          </section>
        )}

        {result.lang_ratio && (
          <section>
            <h3 className="font-semibold text-indigo-200">語言佔比</h3>
            <p className="mt-2 text-white/90">
              中文：{((result.lang_ratio.zh ?? 0) * 100).toFixed(1)}% · 英文：
              {((result.lang_ratio.en ?? 0) * 100).toFixed(1)}% · 其他：
              {((result.lang_ratio.other ?? 0) * 100).toFixed(1)}%
            </p>
          </section>
        )}

        <footer className="border-t border-white/10 pt-4 text-sm text-white/50">
          總留言數：{result.stats?.n_comments ?? 0}
        </footer>
      </div>
    </article>
  );
}
