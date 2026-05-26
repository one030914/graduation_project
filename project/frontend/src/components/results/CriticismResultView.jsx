"use client";

import { clip, fmtList } from "@/lib/analysisFormat";
import { CriticismChart } from "@/components/charts/CriticismChart";
import { InfoTile, ResultCard, ResultFooter, ResultShell } from "@/components/results/ResultCards";

function severityLabel(level) {
  const map = { low: "低", medium: "中", high: "高" };
  return map[level] || level || "未知";
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
    <ResultShell label="Criticism" title={`批評與改善回饋：${clip(result.title || result.video_id, 256)}`}>
      <ResultCard title="批評訊號概況">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <InfoTile label="分析狀態" value={result.status || "ok"} />
          <InfoTile label="分析留言數" value={`${result.analyzed_comments ?? 0} / ${result.total_comments ?? 0}`} />
          <InfoTile label="批評強度" value={severityLabel(result.severity_level)} tone="red" />
          <InfoTile label="主要批評" value={`${result.criticism_count ?? 0} 項`} />
          <InfoTile label="不滿原因" value={`${result.reason_count ?? 0} 項`} />
          <InfoTile label="改進建議" value={`${result.suggestion_count ?? 0} 項`} />
        </div>
        {result.message && <p className="mt-3 text-amber-200">{result.message}</p>}
      </ResultCard>

      {chartData.length > 0 && <CriticismChart data={chartData} />}

      {chartData.length > 0 && (
        <ResultCard title="批評類型分布" tone="red">
          <div className="flex flex-wrap gap-2">
            {chartData.map((item) => (
              <span key={item.key || item.label} className="rounded-full border border-red-300/15 bg-red-400/10 px-3 py-1.5 text-sm font-black text-red-100">
                {item.label}：{item.count}（{fmtPercent(item.value)}）
              </span>
            ))}
          </div>
        </ResultCard>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        {mainCriticisms.length > 0 && (
          <ResultCard title="主要批評與抱怨痛點" tone="red" className="h-full">
            <p className="whitespace-pre-line">{fmtList(mainCriticisms)}</p>
          </ResultCard>
        )}

        {reasons.length > 0 && (
          <ResultCard title="觀眾不滿原因" tone="amber" className="h-full">
            <p className="whitespace-pre-line">{fmtList(reasons)}</p>
          </ResultCard>
        )}

        {suggestions.length > 0 && (
          <ResultCard title="觀眾提出的改進建議" tone="emerald" className="h-full">
            <p className="whitespace-pre-line">{fmtList(suggestions)}</p>
          </ResultCard>
        )}

        {actionItems.length > 0 && (
          <ResultCard title="可轉換為創作者行動" className="h-full">
            <p className="whitespace-pre-line">{fmtList(actionItems)}</p>
          </ResultCard>
        )}
      </div>

      {mainCriticisms.length === 0 && reasons.length === 0 && suggestions.length === 0 && (
        <ResultCard title="批評結果">
          <p>目前沒有形成明確批評、抱怨或改進建議。</p>
        </ResultCard>
      )}

      <ResultFooter>Criticism：資料不足時不代表風向良好。</ResultFooter>
    </ResultShell>
  );
}
