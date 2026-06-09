"use client";

import { useState } from "react";
import { clip, fmtKeywords, fmtList } from "@/lib/analysisFormat";
import { OpinionGauge } from "@/components/charts/OpinionGauge";
import { TopicsBarChart } from "@/components/charts/TopicsBarChart";
import { TimelineLineChart } from "@/components/charts/TimelineLineChart";
import { EmotionRadarChart } from "@/components/charts/EmotionRadarChart";
import { CriticismChart } from "@/components/charts/CriticismChart";
import { KeywordBarChart } from "@/components/charts/KeywordBarChart";
import { VideoChapterTimeline } from "@/components/charts/VideoChapterTimeline";
import { FallbackText, ResultFooter, ResultHeader } from "@/components/results/ResultCards";

function TextCard({ title, children, tone = "indigo", className = "" }) {
  const titleClass = tone === "amber" ? "text-amber-200" : "text-indigo-200";

  return (
    <section
      className={`rounded-2xl border border-white/10 bg-[#070d20]/90 p-6 text-white shadow-[0_18px_48px_rgba(2,6,23,0.3)] ring-1 ring-indigo-300/5 backdrop-blur-md ${className}`}
    >
      <h3 className={`text-xl font-black tracking-normal ${titleClass}`}>{title}</h3>
      <div className="mt-4 text-base font-semibold leading-8 text-white/72">{children}</div>
    </section>
  );
}

function SkeletonLines({ lines = 3 }) {
  return (
    <div className="animate-pulse space-y-3" aria-hidden="true">
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className={`h-4 rounded-full bg-white/10 ${index === lines - 1 ? "w-2/3" : "w-full"}`}
        />
      ))}
    </div>
  );
}

function SkeletonChart() {
  return (
    <div className="animate-pulse space-y-4" aria-hidden="true">
      <div className="h-64 rounded-2xl border border-white/10 bg-white/[0.045]" />
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="h-10 rounded-xl bg-white/10" />
        <div className="h-10 rounded-xl bg-white/10" />
        <div className="h-10 rounded-xl bg-white/10" />
      </div>
    </div>
  );
}

function SkeletonChips() {
  return (
    <div className="flex animate-pulse flex-wrap gap-2" aria-hidden="true">
      {[96, 72, 112, 84, 104, 68].map((width, index) => (
        <div key={index} className="h-8 rounded-full bg-white/10" style={{ width }} />
      ))}
    </div>
  );
}

function TagChips({ tags, isLoading }) {
  return (
    <div>
      <h4 className="text-base font-black tracking-normal text-indigo-200">留言區標籤</h4>
      <div className="mt-3">
        {tags.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {tags.slice(0, 8).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-indigo-300/15 bg-indigo-400/10 px-3 py-1.5 text-base font-black text-indigo-100"
              >
                #{tag}
              </span>
            ))}
          </div>
        ) : isLoading ? (
          <SkeletonChips />
        ) : (
          <FallbackText>目前沒有留言區標籤資料。</FallbackText>
        )}
      </div>
    </div>
  );
}

function isLoadingStatus(value) {
  return ["submitting", "queued", "running", "pending"].includes(String(value || "").toLowerCase());
}

function InfoTile({ label, value }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 ring-1 ring-white/5">
      <p className="text-base font-bold text-white/42">{label}</p>
      <p className="mt-1 break-words text-base font-black text-white/88">{String(value)}</p>
    </div>
  );
}

function getSourceStatusClass(value) {
  const status = String(value).toLowerCase();

  if (status.includes("error")) {
    return "border-rose-300/20 bg-rose-400/10 text-rose-200";
  }

  if (status.includes("insufficient_data")) {
    return "border-amber-300/20 bg-amber-400/10 text-amber-200";
  }

  if (status.includes("ok")) {
    return "border-emerald-300/20 bg-emerald-400/10 text-emerald-200";
  }

  return "border-slate-300/15 bg-slate-400/10 text-slate-200";
}

function SourceStatusStrip({ sources }) {
  const entries = Object.entries(sources);

  const SOURCE_LABELS = {
    summary: "摘要",
    keyword: "關鍵詞",
    emotion: "情緒",
    topics: "主題",
    criticism: "批評",
    timeline: "時間軸",
    video_content: "影片內容",
  };

  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.025] px-4 py-3 text-base font-bold text-white/45">
      {entries.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          <span className="mr-1 text-white/38">子分析來源狀態</span>
          {entries.map(([key, value]) => (
            <span
              key={key}
              className={`rounded-full border px-2.5 py-1 font-black ${getSourceStatusClass(value)}`}
            >
              {SOURCE_LABELS[key] || key}: {String(value)}
            </span>
          ))}
        </div>
      ) : (
        <FallbackText>目前沒有子分析來源狀態資料。</FallbackText>
      )}
    </section>
  );
}

function AdviceToggleContent({
  activeTab,
  creatorActions,
  viewerTips,
  isCreatorLoading,
  isViewerLoading,
  onTabChange,
}) {
  const isCreator = activeTab === "creator";
  const items = isCreator ? creatorActions : viewerTips;
  const isLoading = isCreator ? isCreatorLoading : isViewerLoading;
  const title = isCreator ? "創作者行動建議" : "觀眾觀看提示";
  const fallback = isCreator ? "目前沒有創作者行動建議資料。" : "目前沒有觀眾觀看提示資料。";

  const buttonClassName = (value) => {
    const isActive = activeTab === value;
    return isActive
      ? "border-indigo-200/70 bg-indigo-400/18 text-indigo-100 shadow-[0_0_18px_rgba(129,140,248,0.22)]"
      : "border-white/10 bg-white/[0.04] text-white/55 hover:border-white/25 hover:bg-white/[0.08] hover:text-white/82";
  };

  return (
    <>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-base font-black uppercase tracking-[0.14em] text-indigo-200/70">
            建議
          </p>
          <h3 className="mt-2 text-xl font-black tracking-normal text-indigo-200">{title}</h3>
        </div>
        <div className="inline-flex rounded-xl border border-white/10 bg-white/[0.025] p-1">
          <button
            type="button"
            onClick={() => onTabChange("creator")}
            className={`rounded-lg border px-3 py-2 text-base font-black transition ${buttonClassName("creator")}`}
          >
            創作者
          </button>
          <button
            type="button"
            onClick={() => onTabChange("viewer")}
            className={`rounded-lg border px-3 py-2 text-base font-black transition ${buttonClassName("viewer")}`}
          >
            觀眾
          </button>
        </div>
      </div>

      <div className="mt-5 text-base font-semibold leading-8 text-white/72">
        {items.length > 0 ? (
          <p className="whitespace-pre-line">{fmtList(items)}</p>
        ) : isLoading ? (
          <SkeletonLines lines={3} />
        ) : (
          <FallbackText>{fallback}</FallbackText>
        )}
      </div>
    </>
  );
}

export function AnalysisResultView({ result }) {
  const [activeAdviceTab, setActiveAdviceTab] = useState("creator");

  if (!result) return null;

  if (result.error) {
    return (
      <p className="rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-100">
        {result.error}
      </p>
    );
  }

  if (result.public_opinion_score !== undefined || result.quick_summary !== undefined) {
    const score = Number(result.public_opinion_score ?? 0);
    const label =
      result.opinion_label || (score >= 75 ? "正向偏高" : score >= 50 ? "中性偏穩" : "負面偏高");
    const tags = result.tags ?? [];
    const quickSummary = result.quick_summary ?? [];
    const creatorActions = result.creator_actions ?? [];
    const viewerTips = result.viewer_tips ?? [];
    const topHotspot = result.top_hotspot ?? null;
    const mainEmotion = result.main_emotion || "未知";
    const dataSources = result.data_sources || {};
    const dataQuality = result.data_quality || [];
    const dashboardData = result.dashboard_data ?? {};
    const topicsDashboard = dashboardData.topics ?? {};
    const timelineDashboard = dashboardData.timeline ?? {};
    const emotionDashboard = dashboardData.emotion ?? {};
    const criticismDashboard = dashboardData.criticism ?? {};
    const keywordDashboard = dashboardData.keyword ?? {};
    const videoContentDashboard = dashboardData.video_content ?? {};
    const isSourceLoading = (key) => isLoadingStatus(dataSources[key]);

    return (
      <article className="rounded-3xl border border-white/10 bg-slate-950/35 p-5 shadow-[0_24px_70px_rgba(2,6,23,0.32)] ring-1 ring-indigo-300/5 backdrop-blur-md sm:p-7">
        <ResultHeader
          label="Analyze"
          title={clip(result.title || result.video_id || "YouTube 留言綜合分析", 256)}
        />

        <div className="mt-6 space-y-5">
          {/* 分析範圍 */}
          <TextCard title="分析範圍">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <InfoTile label="總留言數" value={result.total_comments ?? 0} />
              <InfoTile label="主導情緒" value={mainEmotion} />
              <InfoTile label="時間軸狀態" value={result.timeline_status || "unknown"} />
              <InfoTile label="影片內容脈絡" value={dataSources.video_content || "missing"} />
            </div>
          </TextCard>

          {/* 資料品質提醒 */}
          {dataQuality.length > 0 && (
            <TextCard title="資料品質提醒" tone="amber">
              <p className="whitespace-pre-line">{fmtList(dataQuality)}</p>
            </TextCard>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            {/* 整體風向 */}
            {isSourceLoading("emotion") ? (
              <TextCard title="輿情溫度計">
                <SkeletonChart />
              </TextCard>
            ) : (
              <OpinionGauge
                score={emotionDashboard.opinion_score ?? score}
                label={emotionDashboard.opinion_label ?? label}
              />
            )}
            {/* 熱門討論焦點 */}
            {(topicsDashboard.chart_data ?? []).length > 0 ? (
              <TopicsBarChart data={topicsDashboard.chart_data ?? []} />
            ) : (
              <TextCard title="熱門討論焦點">
                {isSourceLoading("topics") ? (
                  <SkeletonChart />
                ) : (
                  <FallbackText>目前沒有可繪製的主題圖表資料。</FallbackText>
                )}
              </TextCard>
            )}
          </div>

          {/* AI 智慧快報 + 建議 */}
          <section className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-6 text-white shadow-[0_18px_48px_rgba(2,6,23,0.3)] ring-1 ring-indigo-300/5 backdrop-blur-md">
            <h3 className="text-xl font-black tracking-normal text-indigo-200">AI 智慧快報</h3>
            <div className="mt-4 text-base font-semibold leading-8 text-white/72">
              {quickSummary.length > 0 ? (
                <p className="whitespace-pre-line">{fmtList(quickSummary)}</p>
              ) : isSourceLoading("summary") ? (
                <SkeletonLines lines={4} />
              ) : (
                <FallbackText>目前沒有 AI 智慧快報資料。</FallbackText>
              )}
            </div>

            <div className="mt-6 border-t border-white/10 pt-6">
              <AdviceToggleContent
                activeTab={activeAdviceTab}
                creatorActions={creatorActions}
                viewerTips={viewerTips}
                isCreatorLoading={isSourceLoading("criticism") || isSourceLoading("video_content")}
                isViewerLoading={isSourceLoading("timeline")}
                onTabChange={setActiveAdviceTab}
              />
            </div>
          </section>

          {/* 情緒心理圖譜 + 批評與改善比例 */}
          <div className="grid gap-5 lg:grid-cols-2">
            {(emotionDashboard.chart_data ?? []).length > 0 ? (
              <EmotionRadarChart data={emotionDashboard.chart_data ?? []} />
            ) : (
              <TextCard title="情緒心理圖譜">
                {isSourceLoading("emotion") ? (
                  <SkeletonChart />
                ) : (
                  <FallbackText>目前沒有可繪製的情緒圖表資料。</FallbackText>
                )}
              </TextCard>
            )}

            {(criticismDashboard.chart_data ?? []).length > 0 ? (
              <CriticismChart data={criticismDashboard.chart_data ?? []} />
            ) : (
              <TextCard title="批評與改善比例">
                {isSourceLoading("criticism") ? (
                  <SkeletonChart />
                ) : (
                  <FallbackText>目前沒有可繪製的批評圖表資料。</FallbackText>
                )}
              </TextCard>
            )}
          </div>

          {/* 熱門關鍵詞 */}
          {(keywordDashboard.chart_data ?? []).length > 0 ? (
            <KeywordBarChart data={keywordDashboard.chart_data ?? []} />
          ) : (
            <TextCard title="熱門關鍵詞">
              {isSourceLoading("keyword") ? (
                <SkeletonChart />
              ) : (
                <FallbackText>目前沒有可繪製的關鍵詞圖表資料。</FallbackText>
              )}
            </TextCard>
          )}

          {/* 留言時間軸熱點 + 留言區標籤 */}
          {(timelineDashboard.chart_data ?? []).length > 0 ? (
            <TimelineLineChart
              data={timelineDashboard.chart_data ?? []}
              hotspot={topHotspot}
              footer={
                <TagChips
                  tags={tags}
                  isLoading={isSourceLoading("keyword") || isSourceLoading("topics")}
                />
              }
            />
          ) : (
            <TextCard title="留言時間軸熱點">
              {isSourceLoading("timeline") ? (
                <SkeletonChart />
              ) : (
                <FallbackText>目前沒有可繪製的時間軸資料。</FallbackText>
              )}
              <div className="mt-6 border-t border-white/10 pt-5">
                <TagChips
                  tags={tags}
                  isLoading={isSourceLoading("keyword") || isSourceLoading("topics")}
                />
              </div>
            </TextCard>
          )}

          {/* 影片內容脈絡 */}
          {(videoContentDashboard.chapter_timeline ?? []).length > 0 ? (
            <VideoChapterTimeline chapters={videoContentDashboard.chapter_timeline ?? []} />
          ) : (
            <TextCard title="影片內容脈絡">
              {isSourceLoading("video_content") ? (
                <SkeletonChart />
              ) : (
                <FallbackText>目前沒有影片章節脈絡資料。</FallbackText>
              )}
            </TextCard>
          )}

          {/* 子分析來源狀態 */}
          <SourceStatusStrip sources={dataSources} />

          <ResultFooter>
            <p>Analyze：整合留言摘要、情緒、主題、批評、關鍵詞、時間軸與影片內容脈絡產生。</p>
            <p>長影片會因字幕分析而需要較久時間，且可能因字幕品質影響分析結果。</p>
          </ResultFooter>
        </div>
      </article>
    );
  }

  return (
    <article className="rounded-3xl border border-white/10 bg-slate-950/35 p-5 shadow-[0_24px_70px_rgba(2,6,23,0.32)] ring-1 ring-indigo-300/5 backdrop-blur-md sm:p-7">
      <ResultHeader
        label="Analysis"
        title={clip(result.title || result.video_id || "綜合分析結果", 256)}
      />

      <div className="mt-6 space-y-5">
        <TextCard title="中文摘要">
          {result.summary_zh?.length > 0 ? (
            <p className="whitespace-pre-line">{fmtList(result.summary_zh)}</p>
          ) : (
            <FallbackText>目前沒有中文摘要資料。</FallbackText>
          )}
        </TextCard>

        <TextCard title="English summary">
          {result.summary_en?.length > 0 ? (
            <p className="whitespace-pre-line">{fmtList(result.summary_en)}</p>
          ) : (
            <FallbackText>No English summary data is available.</FallbackText>
          )}
        </TextCard>

        <TextCard title="中文關鍵字">
          {result.keywords_zh?.length > 0 ? (
            <p>{fmtKeywords(result.keywords_zh)}</p>
          ) : (
            <FallbackText>目前沒有中文關鍵字資料。</FallbackText>
          )}
        </TextCard>

        <TextCard title="English keywords">
          {result.keywords_en?.length > 0 ? (
            <p>{fmtKeywords(result.keywords_en)}</p>
          ) : (
            <FallbackText>No English keyword data is available.</FallbackText>
          )}
        </TextCard>

        <TextCard title="語言佔比">
          {result.lang_ratio ? (
            <div className="grid gap-3 sm:grid-cols-3">
              <InfoTile label="中文" value={`${((result.lang_ratio.zh ?? 0) * 100).toFixed(1)}%`} />
              <InfoTile label="英文" value={`${((result.lang_ratio.en ?? 0) * 100).toFixed(1)}%`} />
              <InfoTile
                label="其他"
                value={`${((result.lang_ratio.other ?? 0) * 100).toFixed(1)}%`}
              />
            </div>
          ) : (
            <FallbackText>目前沒有語言佔比資料。</FallbackText>
          )}
        </TextCard>

        <footer className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-base font-semibold text-white/45">
          總留言數：{result.stats?.n_comments ?? 0}
        </footer>
      </div>
    </article>
  );
}
