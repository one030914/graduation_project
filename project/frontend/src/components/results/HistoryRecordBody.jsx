"use client";

import { AnalysisResultView } from "@/components/results/AnalysisResultView";
import { SummaryResultView } from "@/components/results/SummaryResultView";
import { KeywordResultView } from "@/components/results/KeywordResultView";
import { TopicsResultView } from "@/components/results/TopicsResultView";
import { EmotionRecordView } from "@/components/results/EmotionRecordView";
import { CriticismResultView } from "@/components/results/CriticismResultView";
import { TimelineResultView } from "@/components/results/TimelineResultView";
import { VideoContentResultView } from "@/components/results/VideoContentResultView";

export function HistoryRecordBody({ mode, category, payload }) {
  const data = payload ?? {};

  if (mode === "analyze") {
    return <AnalysisResultView result={data} />;
  }

  if (mode === "summary") {
    return <SummaryResultView result={data} />;
  }

  if (mode === "keyword") {
    return <KeywordResultView result={data} />;
  }

  if (mode === "topics") {
    return <TopicsResultView result={data} />;
  }

  if (mode === "emotion") {
    return <EmotionRecordView result={data} />;
  }

  if (mode === "criticism") {
    return <CriticismResultView result={data} />;
  }

  if (mode === "timeline") {
    return <TimelineResultView result={data} />;
  }

  if (mode === "video_content") {
    return <VideoContentResultView result={data} />;
  }

  return (
    <p className="text-base text-white/60">此紀錄類型無法對應首頁預覽（{category || "未分類"}）。</p>
  );
}
