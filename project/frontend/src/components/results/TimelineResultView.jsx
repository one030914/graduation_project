"use client";

import { clip } from "@/lib/analysisFormat";

function fmtPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

function fmtComments(comments) {
  if (!comments || comments.length === 0) return "無";
  return comments.map((comment) => `> ${comment}`).join("\n");
}

export function TimelineResultView({ result }) {
  if (!result) return null;

  if (result.error || result.status === "error") {
    return (
      <p className="rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-100">
        {result.error || result.message || "時間軸分析失敗"}
      </p>
    );
  }

  const hotspots = result.hotspots ?? [];
  const series = result.series ?? [];
  const chartData = result.chart_data ?? [];

  return (
    <article className="rounded-2xl border border-white/15 bg-gray-900/50 p-6 shadow-inner backdrop-blur-md">
      <h2 className="text-xl font-bold">
        時間軸熱點分析：{clip(result.title || result.video_id, 256)}
      </h2>

      <div className="mt-6 space-y-5">
        <section>
          <h3 className="font-semibold text-indigo-200">時間軸資料概況</h3>
          <p className="mt-2 whitespace-pre-line text-white/90">
            {`分析狀態：${result.status || "ok"}
                        分析留言數：${result.total_comments ?? 0}
                        含時間戳留言：${result.timestamp_comment_count ?? 0} 則（${fmtPercent(result.timestamp_comment_ratio)}）
                        時間戳總提及次數：${result.total_timestamp_mentions ?? 0}
                        時間桶大小：${result.bucket_size ?? 30} 秒
                        最高峰值：${result.peak_count ?? 0} 次 / bucket`}
          </p>
          {result.message && <p className="mt-2 text-sm text-amber-200">{result.message}</p>}
        </section>

        {hotspots.length > 0 ? (
          <>
            <section>
              <h3 className="font-semibold text-orange-200">Top 1 高能片段</h3>
              <p className="mt-2 whitespace-pre-line text-white/90">
                {`${hotspots[0].time_label} 附近｜被提及 ${hotspots[0].count ?? 0} 次
                                ${fmtComments((hotspots[0].representative_comments ?? []).slice(0, 2))}`}
              </p>
            </section>

            {hotspots.length > 1 && (
              <section>
                <h3 className="font-semibold text-indigo-200">其他熱門片段</h3>
                <div className="mt-2 space-y-2">
                  {hotspots.slice(1, 6).map((hotspot, idx) => (
                    <div
                      key={`${hotspot.time_label}-${idx}`}
                      className="rounded-xl border border-white/10 bg-black/20 p-3"
                    >
                      <p className="font-semibold text-white/90">
                        {idx + 2}. {hotspot.time_label} ｜ 被提及 {hotspot.count ?? 0} 次
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        ) : (
          <section>
            <h3 className="font-semibold text-indigo-200">熱點結果</h3>
            <p className="mt-2 text-white/90">目前沒有形成明確時間軸熱點。</p>
          </section>
        )}

        <footer className="border-t border-white/10 pt-4 text-sm text-white/50">
          曲線資料：series {series.length} 筆，chart_data {chartData.length} 筆。
          此分析統計留言中被觀眾主動提及的影片時間點，不是 YouTube 官方重播率。
        </footer>
      </div>
    </article>
  );
}
