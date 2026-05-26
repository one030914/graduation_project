"use client";

import { AnalysisResultView } from "@/components/results/AnalysisResultView";
import { SummaryResultView } from "@/components/results/SummaryResultView";
import { KeywordResultView } from "@/components/results/KeywordResultView";
import { TopicsResultView } from "@/components/results/TopicsResultView";
import { EmotionRecordView } from "@/components/results/EmotionRecordView";
import { CriticismResultView } from "@/components/results/CriticismResultView";
import { TimelineResultView } from "@/components/results/TimelineResultView";
import { VideoContentResultView } from "@/components/results/VideoContentResultView";

export function HistoryRecordBody({ category, payload, youtubeUrl }) {
  const data = payload ?? {};

  if (category === "分析") {
    return <AnalysisResultView result={data} />;
  }

  if (category === "摘要") {
    return <SummaryResultView result={data} />;
  }

  if (category === "關鍵詞") {
    return <KeywordResultView result={data} />;
  }

  if (category === "主題" || category === "主題分析") {
    return <TopicsResultView result={data} />;
  }

  if (category === "情緒" || category === "情緒分析") {
    return <EmotionRecordView youtubeUrl={youtubeUrl} payload={data} />;
  }

  if (category === "批評" || category === "批評分析") {
    return <CriticismResultView result={data} />;
  }

  if (category === "時間軸" || category === "時間軸分析") {
    return <TimelineResultView result={data} />;
  }

  if (category === "影片內容") {
    return <VideoContentResultView result={data} />;
  }

  return (
    <p className="text-sm text-white/60">此紀錄類型無法對應首頁預覽（{category || "未分類"}）。</p>
  );
}
