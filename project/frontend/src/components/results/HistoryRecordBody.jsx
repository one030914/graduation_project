"use client";

import { AnalysisResultView } from "@/components/results/AnalysisResultView";
import { TopicsResultView } from "@/components/results/TopicsResultView";
import { EmotionRecordView } from "@/components/results/EmotionRecordView";

export function HistoryRecordBody({ category, payload, youtubeUrl }) {
  const data = payload ?? {};

  if (category === "分析" || category === "摘要" || category === "關鍵詞") {
    return <AnalysisResultView result={data} />;
  }

  if (category === "主題" || category === "主題分析") {
    return <TopicsResultView result={data} />;
  }

  if (category === "情緒" || category === "情緒分析") {
    return <EmotionRecordView youtubeUrl={youtubeUrl} payload={data} />;
  }

  return (
    <p className="text-sm text-white/60">
      此紀錄類型無法對應首頁預覽（{category || "未分類"}）。
    </p>
  );
}
