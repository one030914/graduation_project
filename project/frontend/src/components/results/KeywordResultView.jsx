"use client";

import { clip, fmtKeywords } from "@/lib/analysisFormat";
import { KeywordBarChart } from "@/components/charts/KeywordBarChart";
import { FallbackText, InfoTile, ResultCard, ResultFooter, ResultShell } from "@/components/results/ResultCards";

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
    <ResultShell
      label="Keyword"
      title={`關鍵詞分析：${clip(result.title || result.video_id, 256)}`}
    >
      <ResultCard title="分析狀態">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <InfoTile label="狀態" value={result.status || "ok"} />
          <InfoTile label="分析留言數" value={result.analyzed_comments ?? 0} />
          <InfoTile label="總留言數" value={result.total_comments ?? 0} />
          <InfoTile label="主要語言" value={result.language || "mixed"} />
        </div>
        {result.message && <p className="mt-3 text-amber-200">{result.message}</p>}
      </ResultCard>

      <ResultCard title="熱門標籤">
        {topTags.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {topTags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-indigo-300/15 bg-indigo-400/10 px-3 py-1.5 text-sm font-black text-indigo-100"
              >
                #{tag}
              </span>
            ))}
          </div>
        ) : (
          <FallbackText>目前沒有熱門標籤資料。</FallbackText>
        )}
      </ResultCard>

      {chartData.length > 0 ? (
        <KeywordBarChart data={chartData} />
      ) : (
        <ResultCard title="熱門關鍵詞圖表">
          <FallbackText>目前沒有可繪製的關鍵詞圖表資料。</FallbackText>
        </ResultCard>
      )}

      <ResultCard title="熱門關鍵詞分布">
        {chartData.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {chartData.slice(0, 12).map((item, idx) => {
              const label = item.keyword || item.label || `keyword-${idx}`;
              const count = item.count ?? 0;
              const ratio = item.ratio ?? 0;

              return (
                <InfoTile
                  key={`${label}-${idx}`}
                  label={label}
                  value={`${count} 則｜${fmtPercent(ratio)}`}
                />
              );
            })}
          </div>
        ) : (
          <FallbackText>目前沒有熱門關鍵詞分布資料。</FallbackText>
        )}
      </ResultCard>

      <ResultCard title="中文關鍵詞">
        {keywordsZh.length > 0 ? <p>{fmtKeywords(keywordsZh)}</p> : <FallbackText>目前沒有中文關鍵詞資料。</FallbackText>}
      </ResultCard>

      <ResultCard title="English Keywords">
        {keywordsEn.length > 0 ? <p>{fmtKeywords(keywordsEn)}</p> : <FallbackText>No English keyword data is available.</FallbackText>}
      </ResultCard>

      <ResultFooter>文字雲資料：{wordcloudData.length} 個詞項，可供後續圖表顯示。</ResultFooter>
    </ResultShell>
  );
}
