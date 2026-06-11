"use client";

import { clip, fmtList } from "@/lib/analysisFormat";
import { CriticismChart } from "@/components/charts/CriticismChart";
import {
  FallbackText,
  InfoTile,
  ResultCard,
  ResultFooter,
  ResultShell,
} from "@/components/results/ResultCards";

function severityLabel(level) {
  const map = { low: "低", medium: "中", high: "高" };
  return map[level] || level || "未知";
}

function severityTone(level) {
  const map = { low: "emerald", medium: "amber", high: "red" };
  return map[level] || "indigo";
}

function fmtPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

export function CriticismResultView({ result }) {
  if (!result) return null;

  if (result.error) {
    return (
      <p className="rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-100">
        {result.error}
      </p>
    );
  }

  const mainCriticisms = result.main_criticisms ?? [];
  const reasons = result.discontent_reasons ?? [];
  const suggestions = result.suggestions ?? [];
  const actionItems = result.action_items ?? [];
  const chartData = result.chart_data ?? [];

  return (
    <ResultShell label="Criticism" title={clip(result.title || result.video_id, 256)}>
      <ResultCard title="分析概況">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <InfoTile label="分析狀態" value={result.status || "ok"} />
          <InfoTile
            label="分析留言數"
            value={`${result.analyzed_comments ?? 0} / ${result.total_comments ?? 0}`}
          />
          <InfoTile
            label="批評強度"
            value={severityLabel(result.severity_level)}
            tone={severityTone(result.severity_level)}
          />
          <InfoTile label="主要批評" value={`${result.criticism_count ?? 0} 項`} />
          <InfoTile label="不滿原因" value={`${result.reason_count ?? 0} 項`} />
          <InfoTile label="改進建議" value={`${result.suggestion_count ?? 0} 項`} />
        </div>
        {result.message && <p className="mt-3 text-amber-200">{result.message}</p>}
      </ResultCard>

      {chartData.length > 0 ? (
        <CriticismChart data={chartData} />
      ) : (
        <ResultCard title="批評圖表" tone="red">
          <FallbackText>目前沒有可繪製的批評類型圖表資料。</FallbackText>
        </ResultCard>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <ResultCard title="主要批評與抱怨痛點" tone="red" className="h-full">
          {mainCriticisms.length > 0 ? (
            <p className="whitespace-pre-line">{fmtList(mainCriticisms)}</p>
          ) : (
            <FallbackText>目前沒有主要批評與抱怨痛點資料。</FallbackText>
          )}
        </ResultCard>

        <ResultCard title="觀眾不滿原因" tone="amber" className="h-full">
          {reasons.length > 0 ? (
            <p className="whitespace-pre-line">{fmtList(reasons)}</p>
          ) : (
            <FallbackText>目前沒有觀眾不滿原因資料。</FallbackText>
          )}
        </ResultCard>

        <ResultCard title="觀眾提出的改進建議" tone="emerald" className="h-full">
          {suggestions.length > 0 ? (
            <p className="whitespace-pre-line">{fmtList(suggestions)}</p>
          ) : (
            <FallbackText>目前沒有改進建議資料。</FallbackText>
          )}
        </ResultCard>

        <ResultCard title="可轉換為創作者行動" className="h-full">
          {actionItems.length > 0 ? (
            <p className="whitespace-pre-line">{fmtList(actionItems)}</p>
          ) : (
            <FallbackText>目前沒有可轉換為創作者行動的資料。</FallbackText>
          )}
        </ResultCard>
      </div>

      <ResultFooter>
        Criticism：整理留言中的主要批評、不滿原因與改進建議，協助判斷觀眾對影片的負面回饋來源。資料不足時不代表風向良好。
      </ResultFooter>
    </ResultShell>
  );
}
