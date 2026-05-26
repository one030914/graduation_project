"use client";

import { fmtKeywords } from "@/lib/analysisFormat";
import { TopicsBarChart } from "@/components/charts/TopicsBarChart";
import { InfoTile, ResultCard, ResultFooter, ResultShell } from "@/components/results/ResultCards";

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

  return (
    <ResultShell label="Topics" title={`主題分析：${result.title || result.video_id || "未命名影片"}`}>
      <ResultCard title="分析概況">
        <div className="grid gap-3 sm:grid-cols-3">
          <InfoTile label="主要語言" value={result.language === "zh" ? "中文" : "英文"} />
          <InfoTile label="主題數" value={result.topics?.length ?? 0} />
          <InfoTile label="參與留言數" value={result.total_comments ?? 0} />
        </div>
      </ResultCard>

      {chartData.length > 0 && <TopicsBarChart data={chartData} />}

      {result.topics?.length > 0 && (
        <div className="grid gap-5 lg:grid-cols-2">
          {result.topics.map((topic, idx) => {
            const topicName = topic.topic_name || topic.chart_label || `Topic ${idx + 1}`;
            return (
              <ResultCard key={`${topic.cluster_id ?? idx}-${idx}`} title={topicName} className="h-full">
                <div className="grid gap-3 sm:grid-cols-2">
                  <InfoTile label="留言數" value={topic.size || 0} />
                  <InfoTile label="比例" value={`${((topic.ratio || 0) * 100).toFixed(1)}%`} />
                </div>
                <p className="mt-4">關鍵詞：{fmtKeywords(topic.keywords)}</p>
                <p className="mt-3 whitespace-pre-line text-white/62">
                  代表留言：
{topic.representative_comments?.join("\n") || "無"}
                </p>
              </ResultCard>
            );
          })}
        </div>
      )}

      <ResultFooter>參與主題分析留言數：{result.total_comments}</ResultFooter>
    </ResultShell>
  );
}
