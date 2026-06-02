"use client";

import { clip, fmtKeywords, fmtList } from "@/lib/analysisFormat";
import { OpinionGauge } from "@/components/charts/OpinionGauge";
import { TopicsBarChart } from "@/components/charts/TopicsBarChart";
import { TimelineLineChart } from "@/components/charts/TimelineLineChart";
import { EmotionRadarChart } from "@/components/charts/EmotionRadarChart";
import { CriticismChart } from "@/components/charts/CriticismChart";
import { KeywordBarChart } from "@/components/charts/KeywordBarChart";
import { VideoChapterTimeline } from "@/components/charts/VideoChapterTimeline";
import { FallbackText, ResultFooter } from "@/components/results/ResultCards";

function TextCard({ title, children, tone = "indigo", className = "" }) {
  const titleClass = tone === "amber" ? "text-amber-200" : "text-indigo-200";

  return (
    <section
      className={`rounded-2xl border border-white/10 bg-[#070d20]/90 p-6 text-white shadow-[0_18px_48px_rgba(2,6,23,0.3)] ring-1 ring-indigo-300/5 backdrop-blur-md ${className}`}
    >
      <h3 className={`text-lg font-black tracking-normal ${titleClass}`}>{title}</h3>
      <div className="mt-4 text-sm font-semibold leading-7 text-white/72">{children}</div>
    </section>
  );
}

function InfoTile({ label, value }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 ring-1 ring-white/5">
      <p className="text-xs font-bold text-white/42">{label}</p>
      <p className="mt-1 break-words text-sm font-black text-white/88">{String(value)}</p>
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
    <section className="rounded-2xl border border-white/10 bg-white/[0.025] px-4 py-3 text-xs font-bold text-white/45">
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

export function AnalysisResultView({ result }) {
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

    return (
      <article className="rounded-3xl border border-white/10 bg-slate-950/35 p-5 shadow-[0_24px_70px_rgba(2,6,23,0.32)] ring-1 ring-indigo-300/5 backdrop-blur-md sm:p-7">
        <div className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-6 shadow-[0_18px_48px_rgba(2,6,23,0.28)]">
          <p className="text-xs font-black uppercase tracking-[0.18em] text-indigo-200/70">
            YouTube 留言綜合分析
          </p>
          <h2 className="mt-2 text-2xl font-black leading-tight tracking-normal text-white">
            標題：{clip(result.title || result.video_id, 256)}
          </h2>
        </div>

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
          <TextCard title="資料品質提醒" tone="amber">
            {dataQuality.length > 0 ? (
              <p className="whitespace-pre-line">{fmtList(dataQuality)}</p>
            ) : (
              <FallbackText>目前沒有資料品質提醒。</FallbackText>
            )}
          </TextCard>

          <div className="grid gap-4 lg:grid-cols-2">
            {/* 整體風向 */}
            <OpinionGauge
              score={emotionDashboard.opinion_score ?? score}
              label={emotionDashboard.opinion_label ?? label}
            />
            {/* 熱門討論焦點 */}
            {(topicsDashboard.chart_data ?? []).length > 0 ? (
              <TopicsBarChart data={topicsDashboard.chart_data ?? []} />
            ) : (
              <TextCard title="熱門討論焦點">
                <FallbackText>目前沒有可繪製的主題圖表資料。</FallbackText>
              </TextCard>
            )}
          </div>

          {/* AI 智慧快報 */}
          <TextCard title="AI 智慧快報">
            {quickSummary.length > 0 ? (
              <p className="whitespace-pre-line">{fmtList(quickSummary)}</p>
            ) : (
              <FallbackText>目前沒有 AI 智慧快報資料。</FallbackText>
            )}
          </TextCard>

          {/* 留言區標籤 */}
          <TextCard title="留言區標籤">
            {tags.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {tags.slice(0, 8).map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full border border-indigo-300/15 bg-indigo-400/10 px-3 py-1.5 text-sm font-black text-indigo-100"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            ) : (
              <FallbackText>目前沒有留言區標籤資料。</FallbackText>
            )}
          </TextCard>

          {/* 情緒心理圖譜 */}
          {(emotionDashboard.chart_data ?? []).length > 0 ? (
            <EmotionRadarChart data={emotionDashboard.chart_data ?? []} />
          ) : (
            <TextCard title="情緒心理圖譜">
              <FallbackText>目前沒有可繪製的情緒圖表資料。</FallbackText>
            </TextCard>
          )}

          {/* 批評與改善訊號 */}
          {(criticismDashboard.chart_data ?? []).length > 0 ? (
            <CriticismChart data={criticismDashboard.chart_data ?? []} />
          ) : (
            <TextCard title="批評與改善訊號">
              <FallbackText>目前沒有可繪製的批評圖表資料。</FallbackText>
            </TextCard>
          )}

          {/* 熱門關鍵詞 */}
          {(keywordDashboard.chart_data ?? []).length > 0 ? (
            <KeywordBarChart data={keywordDashboard.chart_data ?? []} />
          ) : (
            <TextCard title="熱門關鍵詞">
              <FallbackText>目前沒有可繪製的關鍵詞圖表資料。</FallbackText>
            </TextCard>
          )}

          {/* 留言時間軸熱點 */}
          {(timelineDashboard.chart_data ?? []).length > 0 ? (
            <TimelineLineChart data={timelineDashboard.chart_data ?? []} hotspot={topHotspot} />
          ) : (
            <TextCard title="留言時間軸熱點">
              <FallbackText>目前沒有可繪製的時間軸資料。</FallbackText>
            </TextCard>
          )}

          {/* 影片內容脈絡 */}
          {(videoContentDashboard.chapter_timeline ?? []).length > 0 ? (
            <VideoChapterTimeline chapters={videoContentDashboard.chapter_timeline ?? []} />
          ) : (
            <TextCard title="影片內容脈絡">
              <FallbackText>目前沒有影片章節脈絡資料。</FallbackText>
            </TextCard>
          )}

          <div className="grid gap-5 lg:grid-cols-2">
            {/* 創作者行動建議 */}
            <TextCard title="創作者行動建議" className="h-full">
              {creatorActions.length > 0 ? (
                <p className="whitespace-pre-line">{fmtList(creatorActions)}</p>
              ) : (
                <FallbackText>目前沒有創作者行動建議資料。</FallbackText>
              )}
            </TextCard>

            {/* 觀眾觀看提示 */}
            <TextCard title="觀眾觀看提示" className="h-full">
              {viewerTips.length > 0 ? (
                <p className="whitespace-pre-line">{fmtList(viewerTips)}</p>
              ) : (
                <FallbackText>目前沒有觀眾觀看提示資料。</FallbackText>
              )}
            </TextCard>
          </div>

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
      <div className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-6 shadow-[0_18px_48px_rgba(2,6,23,0.28)]">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-indigo-200/70">
          Analysis Result
        </p>
        <h2 className="mt-2 text-2xl font-black leading-tight tracking-normal text-white">
          標題：{clip(result.title || result.video_id, 256)}
        </h2>
      </div>

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

        <footer className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-sm font-semibold text-white/45">
          總留言數：{result.stats?.n_comments ?? 0}
        </footer>
      </div>
    </article>
  );
}
