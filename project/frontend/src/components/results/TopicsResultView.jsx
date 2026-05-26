"use client";

import { fmtKeywords } from "@/lib/analysisFormat";

export function TopicsResultView({ result }) {
  if (!result) return null;

  if (result.error) {
    return (
      <p className="rounded-xl border border-amber-500/30 bg-amber-950/30 px-4 py-3 text-amber-100">
        {result.error}
      </p>
    );
  }

  const topic = result.topics?.[0] || {};
  const topicName = topic.topic_name || topic.chart_label || `Topic ${idx + 1}`;

  return (
    <article className="rounded-2xl border border-white/15 bg-gray-900/50 p-6 backdrop-blur-md">
      <h2 className="text-xl font-bold">標題：{result.title}</h2>
      <p className="mt-1 text-m text-white/65">
        主要語言：{result.language === "zh" ? "中文" : "英文"}
      </p>

      <div className="mt-6 space-y-6">
        {result.topics?.map((topic, idx) => (
          <section
            key={`${topic.cluster_id ?? idx}-${idx}`}
            className="rounded-xl border border-white/10 bg-black/20 p-4"
          >
            <h3 className="font-semibold text-sky-200">
              {topicName}（{topic.size || 0} 則 · {((topic.ratio || 0) * 100).toFixed(1)}%）
            </h3>
            <p className="mt-2 text-sm text-white/90">關鍵詞：{fmtKeywords(topic.keywords)}</p>
            <p className="mt-2 whitespace-pre-line text-sm text-white/85">
              代表留言：
              <br />
              {topic.representative_comments?.join("\n") || "無"}
            </p>
          </section>
        ))}
      </div>

      <p className="mt-6 text-sm text-white/55">參與主題分析留言數：{result.total_comments}</p>
    </article>
  );
}
