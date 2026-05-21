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

  if (result.public_opinion_score !== undefined || result.quick_summary !== undefined) {
    const score = Number(result.public_opinion_score ?? 0);
    const label = result.opinion_label || (score >= 75 ? "正向偏高" : score >= 50 ? "中性偏穩" : "負面偏高");
    const tags = result.tags ?? [];
    const quickSummary = result.quick_summary ?? [];
    const creatorActions = result.creator_actions ?? [];
    const viewerTips = result.viewer_tips ?? [];
    const topTopics = result.top_topics ?? [];
    const topHotspot = result.top_hotspot ?? null;

    return (
      <article className="rounded-2xl border border-white/15 bg-gray-900/50 p-6 shadow-inner backdrop-blur-md">
        <h2 className="text-xl font-bold">標題：{clip(result.title || result.video_id, 256)}</h2>

        <div className="mt-6 space-y-5">
          <section>
            <h3 className="font-semibold text-indigo-200">整體風向</h3>
            <p className="mt-2 text-white/90">{label} · {score}/100</p>
          </section>

          {quickSummary.length > 0 && (
            <section>
              <h3 className="font-semibold text-indigo-200">AI 智慧快報</h3>
              <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(quickSummary)}</p>
            </section>
          )}

          {tags.length > 0 && (
            <section>
              <h3 className="font-semibold text-indigo-200">留言區標籤</h3>
              <p className="mt-2 text-white/90">{tags.map((tag) => `#${tag}`).join(" ")}</p>
            </section>
          )}

          {topTopics.length > 0 && (
            <section>
              <h3 className="font-semibold text-indigo-200">熱門討論主題</h3>
              <p className="mt-2 text-white/90">{fmtKeywords(topTopics)}</p>
            </section>
          )}

          {topHotspot && (
            <section>
              <h3 className="font-semibold text-indigo-200">最高討論片段</h3>
              <p className="mt-2 whitespace-pre-line text-white/90">
                {topHotspot.time_label} 附近被留言提及 {topHotspot.count ?? 0} 次
                {topHotspot.representative_comment ? `\n${topHotspot.representative_comment}` : ""}
              </p>
            </section>
          )}

          {creatorActions.length > 0 && (
            <section>
              <h3 className="font-semibold text-indigo-200">創作者行動建議</h3>
              <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(creatorActions)}</p>
            </section>
          )}

          {viewerTips.length > 0 && (
            <section>
              <h3 className="font-semibold text-indigo-200">觀眾觀看提示</h3>
              <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(viewerTips)}</p>
            </section>
          )}

          <footer className="border-t border-white/10 pt-4 text-sm text-white/50">
            總留言數：{result.total_comments ?? 0}
          </footer>
        </div>
      </article>
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
