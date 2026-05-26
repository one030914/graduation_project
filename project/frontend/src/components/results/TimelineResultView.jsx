"use client";

import { clip } from "@/lib/analysisFormat";
import { TimelineLineChart } from "@/components/charts/TimelineLineChart";
import { InfoTile, ResultCard, ResultFooter, ResultShell } from "@/components/results/ResultCards";

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
  const topHotspot = hotspots[0]
    ? {
        time_label: hotspots[0].time_label,
        count: hotspots[0].count,
        representative_comment: hotspots[0].representative_comments?.[0],
      }
    : null;

  return (
    <ResultShell
      label="Timeline"
      title={`時間軸熱點分析：${clip(result.title || result.video_id, 256)}`}
    >
      <ResultCard title="時間軸資料概況">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <InfoTile label="分析狀態" value={result.status || "ok"} />
          <InfoTile label="分析留言數" value={result.total_comments ?? 0} />
          <InfoTile
            label="含時間戳留言"
            value={`${result.timestamp_comment_count ?? 0} 則（${fmtPercent(result.timestamp_comment_ratio)}）`}
          />
          <InfoTile label="時間戳總提及" value={result.total_timestamp_mentions ?? 0} />
          <InfoTile label="時間桶大小" value={`${result.bucket_size ?? 30} 秒`} />
          <InfoTile label="最高峰值" value={`${result.peak_count ?? 0} 次 / bucket`} />
        </div>
        {result.message && <p className="mt-3 text-amber-200">{result.message}</p>}
      </ResultCard>

      {chartData.length > 0 && <TimelineLineChart data={chartData} hotspot={topHotspot} />}

      {hotspots.length > 0 ? (
        <>
          <ResultCard title="Top 1 高能片段" tone="amber">
            <p className="whitespace-pre-line">
              {`${hotspots[0].time_label} 附近｜被提及 ${hotspots[0].count ?? 0} 次
${fmtComments((hotspots[0].representative_comments ?? []).slice(0, 2))}`}
            </p>
          </ResultCard>

          {hotspots.length > 1 && (
            <ResultCard title="其他熱門片段">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {hotspots.slice(1, 6).map((hotspot, idx) => (
                  <InfoTile
                    key={`${hotspot.time_label}-${idx}`}
                    label={`${idx + 2}. ${hotspot.time_label}`}
                    value={`被提及 ${hotspot.count ?? 0} 次`}
                  />
                ))}
              </div>
            </ResultCard>
          )}
        </>
      ) : (
        <ResultCard title="熱點結果">
          <p>目前沒有形成明確時間軸熱點。</p>
        </ResultCard>
      )}

      <ResultFooter>
        曲線資料：series {series.length} 筆，chart_data {chartData.length}{" "}
        筆。此分析統計留言中被觀眾主動提及的影片時間點，不是 YouTube 官方重播率。
      </ResultFooter>
    </ResultShell>
  );
}
