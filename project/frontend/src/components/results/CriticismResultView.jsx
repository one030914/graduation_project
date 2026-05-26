"use client";

import { clip, fmtList } from "@/lib/analysisFormat";

function severityLabel(level) {
  const map = {
    low: "低",
    medium: "中",
    high: "高",
  };
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
    <article className="rounded-2xl border border-white/15 bg-gray-900/50 p-6 shadow-inner backdrop-blur-md">
      <h2 className="text-xl font-bold">
        批評與改善回饋：{clip(result.title || result.video_id, 256)}
      </h2>

      <div className="mt-6 space-y-5">
        <section>
          <h3 className="font-semibold text-indigo-200">批評訊號概況</h3>
          <p className="mt-2 whitespace-pre-line text-white/90">
            {`分析狀態：${result.status || "ok"}
                        分析留言數：${result.analyzed_comments ?? 0} / ${result.total_comments ?? 0}
                        批評強度：${severityLabel(result.severity_level)}
                        主要批評：${result.criticism_count ?? 0} 項
                        不滿原因：${result.reason_count ?? 0} 項
                        改進建議：${result.suggestion_count ?? 0} 項`}
          </p>
          {result.message && <p className="mt-2 text-sm text-amber-200">{result.message}</p>}
        </section>

        {chartData.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">批評類型分布</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {chartData.map((item) => (
                <span
                  key={item.key || item.label}
                  className="rounded-full bg-red-500/15 px-3 py-1 text-sm text-red-100"
                >
                  {item.label}：{item.count}（{fmtPercent(item.value)}）
                </span>
              ))}
            </div>
          </section>
        )}

        {mainCriticisms.length > 0 && (
          <section>
            <h3 className="font-semibold text-red-200">主要批評與抱怨痛點</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(mainCriticisms)}</p>
          </section>
        )}

        {reasons.length > 0 && (
          <section>
            <h3 className="font-semibold text-amber-200">觀眾不滿原因</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(reasons)}</p>
          </section>
        )}

        {suggestions.length > 0 && (
          <section>
            <h3 className="font-semibold text-emerald-200">觀眾提出的改進建議</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(suggestions)}</p>
          </section>
        )}

        {actionItems.length > 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">可轉換為創作者行動</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(actionItems)}</p>
          </section>
        )}

        {mainCriticisms.length === 0 && reasons.length === 0 && suggestions.length === 0 && (
          <section>
            <h3 className="font-semibold text-indigo-200">批評結果</h3>
            <p className="mt-2 text-white/90">目前沒有形成明確批評、抱怨或改進建議。</p>
          </section>
        )}

        <footer className="border-t border-white/10 pt-4 text-sm text-white/50">
          Criticism：資料不足時不代表風向良好。
        </footer>
      </div>
    </article>
  );
}
