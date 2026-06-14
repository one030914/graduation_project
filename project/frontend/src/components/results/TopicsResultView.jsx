"use client";

import { clip } from "@/lib/analysisFormat";
import { TopicsBarChart } from "@/components/charts/TopicsBarChart";
import { FallbackText, InfoTile, ResultCard, ResultFooter, ResultShell } from "@/components/results/ResultCards";

function KeywordChips({ keywords }) {
  const items = Array.isArray(keywords)
    ? keywords
        .map((keyword) => String(keyword).trim())
        .filter(Boolean)
        .slice(0, 12)
    : [];

  if (items.length === 0) {
    return <p className="text-base font-semibold text-white/45">無關鍵詞</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((keyword, index) => (
        <span
          key={`${keyword}-${index}`}
          className="rounded-full border border-sky-200/15 bg-sky-300/10 px-3 py-1 text-base font-black leading-5 text-sky-100 ring-1 ring-white/5"
        >
          {clip(keyword, 28)}
        </span>
      ))}
    </div>
  );
}

function RepresentativeComments({ comments }) {
  const items = Array.isArray(comments)
    ? comments
        .map((comment) => String(comment).trim())
        .filter(Boolean)
        .slice(0, 3)
    : [];

  if (items.length === 0) {
    return <p className="text-base font-semibold text-white/45">尚無代表留言</p>;
  }

  return (
    <div className="space-y-2.5">
      {items.map((comment, index) => (
        <blockquote
          key={`${comment}-${index}`}
          className="border-l-2 border-indigo-300/35 bg-white/[0.045] px-4 py-3 text-base font-semibold leading-6 text-white/72"
        >
          <p className="break-words">{clip(comment, 260)}</p>
        </blockquote>
      ))}
    </div>
  );
}

export function TopicsResultView({ result }) {
  if (!result) return null;

  if (result.error) {
    return (
      <p className="rounded-xl border border-amber-500/30 bg-amber-950/30 px-4 py-3 text-amber-100">
        {result.error}
      </p>
    );
  }

  const chartData = result.chart_data ?? [];
  const topics = result.topics ?? [];
  const languageLabel =
    result.language === "zh" ? "中文" : result.language === "en" ? "英文" : "中英混合";
  const coverageRatio = Number(result.coverage_ratio || 0);
  const coverageLabel = `${(coverageRatio * 100).toFixed(1)}%`;
  const statusLabel =
    result.status === "ok" ? "正常" : result.status === "insufficient_data" ? "資料不足" : "錯誤";

  return (
    <ResultShell
      label="Topics"
      title={result.title || result.video_id || "未命名影片"}
    >
      <ResultCard title="分析概況">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <InfoTile label="主要語言" value={languageLabel} />
          <InfoTile label="主題數" value={topics.length} />
          <InfoTile label="可分析留言" value={result.analyzed_comments ?? 0} />
          <InfoTile label="分群覆蓋率" value={coverageLabel} />
          <InfoTile label="分析狀態" value={statusLabel} />
        </div>
      </ResultCard>

      {result.message ? (
        <ResultCard title="資料品質提醒">
          <p>{result.message}</p>
        </ResultCard>
      ) : null}

      {chartData.length > 0 ? (
        <TopicsBarChart data={chartData} />
      ) : (
        <ResultCard title="主題圖表">
          <FallbackText>目前沒有可繪製的主題圖表資料。</FallbackText>
        </ResultCard>
      )}

      {topics.length > 0 ? (
        <div className="columns-1 gap-3 lg:columns-2 [&>*]:mb-3">
          {topics.map((topic, idx) => {
            const topicName = topic.topic_name || topic.chart_label || `Topic ${idx + 1}`;
            const ratio = Number(topic.ratio || 0);

            return (
              <ResultCard
                key={`${topic.cluster_id ?? idx}-${idx}`}
                title={topicName}
                className="break-inside-avoid"
              >
                <div className="grid gap-2 sm:grid-cols-2">
                  <InfoTile label="留言數" value={topic.size || 0} />
                  <InfoTile label="主題占比" value={`${(ratio * 100).toFixed(1)}%`} />
                </div>

                <div className="mt-4 space-y-3 rounded-xl border border-sky-200/10 bg-sky-300/[0.045] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="text-base font-black uppercase tracking-[0.14em] text-sky-200/75">
                      主題關鍵詞
                    </h4>
                    <span className="text-base font-bold text-white/35">
                      {topic.keywords?.length ?? 0} 則
                    </span>
                  </div>
                  <KeywordChips keywords={topic.keywords} />
                </div>

                <div className="mt-4 space-y-3 rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="text-base font-black uppercase tracking-[0.14em] text-indigo-200/75">
                      代表留言
                    </h4>
                    <span className="text-base font-bold text-white/35">
                      {topic.representative_comments?.length ?? 0} 則
                    </span>
                  </div>
                  <RepresentativeComments comments={topic.representative_comments} />
                </div>
              </ResultCard>
            );
          })}
        </div>
      ) : (
        <ResultCard title="主題列表">
          <FallbackText>目前沒有形成可顯示的主題。</FallbackText>
        </ResultCard>
      )}

      <ResultFooter>
        Topics：根據留言語言與內容相似度整理主要討論群組。
        主題占比與代表留言可用來判斷留言區討論焦點；資料不足時結果僅供參考。
      </ResultFooter>
    </ResultShell>
  );
}
