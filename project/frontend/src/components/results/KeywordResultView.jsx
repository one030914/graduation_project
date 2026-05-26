"use client";

import { clip, fmtKeywords } from "@/lib/analysisFormat";

function fmtPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

export function KeywordResultView({ result }) {
  if (!result) return null;

  if (result.error) {
    return (
      <p className="rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-100">
        {result.error}
      </p>
    );
  }

  const topTags = result.top_tags ?? [];
  const chartData = result.chart_data ?? [];
  const keywordsZh = result.keywords_zh ?? [];
  const keywordsEn = result.keywords_en ?? [];
  const wordcloudData = result.wordcloud_data ?? [];

  return (
    <article className="rounded-2xl border border-white/15 bg-gray-900/50 p-6 shadow-inner backdrop-blur-md">
      <h2 className="text-xl font-bold">
        關鍵詞分析：{clip(result.title || result.video_id, 256)}
      </h2>

      <div className="mt-6 space-y-5">
        <section>
          <h3 className="font-semibold text-indigo-200">分析狀態</h3>
          <p className="mt-2 text-white/90">
            {result.status || "ok"} ｜ 分析留言數：{result.analyzed_comments ?? 0} /{" "}
            {result.total_comments ?? 0} ｜ 主要語言：{result.language || "mixed"}
          </p>
          {result.message && <p className="mt-2 text-sm text-amber-200">{result.message}</p>}
        </section>

        {topTags.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">熱門標籤</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {topTags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-indigo-500/20 px-3 py-1 text-sm text-indigo-100"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </section>
        )}

        {chartData.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">熱門關鍵詞分布</h3>
            <div className="mt-3 space-y-2">
              {chartData.slice(0, 12).map((item, idx) => {
                const label = item.keyword || item.label || `keyword-${idx}`;
                const count = item.count ?? 0;
                const ratio = item.ratio ?? 0;

                return (
                  <div
                    key={`${label}-${idx}`}
                    className="rounded-xl border border-white/10 bg-black/20 p-3"
                  >
                    <div className="flex justify-between gap-3 text-sm">
                      <span className="font-semibold text-white/90">{label}</span>
                      <span className="text-white/60">
                        {count} 則｜{fmtPercent(ratio)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {keywordsZh.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">中文關鍵詞</h3>
            <p className="mt-2 text-white/90">{fmtKeywords(keywordsZh)}</p>
          </section>
        )}

        {keywordsEn.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">English Keywords</h3>
            <p className="mt-2 text-white/90">{fmtKeywords(keywordsEn)}</p>
          </section>
        )}

        <footer className="border-t border-white/10 pt-4 text-sm text-white/50">
          文字雲資料：{wordcloudData.length} 個詞項，可供後續圖表顯示。
        </footer>
      </div>
    </article>
  );
}
