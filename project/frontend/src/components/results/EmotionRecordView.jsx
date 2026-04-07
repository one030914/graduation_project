/* eslint-disable @next/next/no-img-element */
"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/apiBase";

export function EmotionRecordView({ youtubeUrl, payload }) {
  const chartFromDb = payload?.emotion_chart_png_base64
    ? `data:image/png;base64,${payload.emotion_chart_png_base64}`
    : null;

  const [fetchedBlobUrl, setFetchedBlobUrl] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [loading, setLoading] = useState(!chartFromDb);
  const [emotionSubPanel, setEmotionSubPanel] = useState(null);
  const [emotionTopicsResult, setEmotionTopicsResult] = useState(null);
  const [trendChart, setTrendChart] = useState(null);
  const [combinedChart, setCombinedChart] = useState(null);
  const [negativePeakAnalysis, setNegativePeakAnalysis] = useState(null);
  const [subPanelLoading, setSubPanelLoading] = useState(false);
  const [combinedChartError, setCombinedChartError] = useState(null);

  const EMOTION_PANEL = { topics: "topics", trend: "trend", combined: "combined" };
  const imageSrc = chartFromDb || fetchedBlobUrl;

  useEffect(() => {
    if (chartFromDb) {
      setFetchedBlobUrl(null);
      setLoading(false);
      setLoadError(null);
      return undefined;
    }

    if (!youtubeUrl) {
      setLoading(false);
      setLoadError("缺少影片網址");
      return undefined;
    }

    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    setFetchedBlobUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/emotion_image`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: youtubeUrl }),
        });
        if (!res.ok) throw new Error("無法取得情緒圖");
        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        if (cancelled) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        setFetchedBlobUrl(objectUrl);
      } catch (e) {
        if (!cancelled) setLoadError(e.message || "載入失敗");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      setFetchedBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    };
  }, [youtubeUrl, chartFromDb]);

  useEffect(() => {
    return () => {
      if (trendChart) URL.revokeObjectURL(trendChart);
      if (combinedChart) URL.revokeObjectURL(combinedChart);
    };
  }, [trendChart, combinedChart]);  

  const handleEmotionTopics = async () => {
    if (!youtubeUrl || subPanelLoading) return;
    setSubPanelLoading(true);
    setEmotionSubPanel(EMOTION_PANEL.topics);
    setTrendChart(null);
    setCombinedChart(null);

    try {
      const res = await fetch(`${API_BASE}/emotion_topics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: youtubeUrl }),
      });
      const data = await res.json();
      setEmotionTopicsResult(data.error ? { error: data.error } : data);
    } catch {
      setEmotionTopicsResult({ error: "取得情緒話題失敗" });
    }

    setSubPanelLoading(false);
  };

  const handleTrendChart = async () => {
    if (!youtubeUrl || subPanelLoading) return;
    setTrendChart((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });

    setSubPanelLoading(true);
    setEmotionSubPanel(EMOTION_PANEL.trend);
    setEmotionTopicsResult(null);
    setCombinedChartError(null);
    setNegativePeakAnalysis(null);

    setCombinedChart((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });

    try {
      const res = await fetch(`${API_BASE}/trend_chart`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: youtubeUrl, chart_type: "sentiment", time_unit: "hour" }),
      });

      if (!res.ok) throw new Error("無法取得趨勢圖表");
      const blob = await res.blob();
      setTrendChart(URL.createObjectURL(blob));

      try {
        const trendRes = await fetch(`${API_BASE}/trend_analysis`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: youtubeUrl, time_unit: "hour" }),
        });
        const trendData = await trendRes.json();

        if (trendData.trend_stats && trendData.trend_stats.negative_peak_analysis) {
          setNegativePeakAnalysis(trendData.trend_stats.negative_peak_analysis);
        } else {
          setNegativePeakAnalysis({ error: "沒有找到負面情緒高峰" });
        }
      } catch {
        setNegativePeakAnalysis({ error: "獲取負面情緒高峰分析失敗" });
      }
    } catch (err) {
      setNegativePeakAnalysis({ error: err.message || "無法取得趨勢圖表" });
    }

    setSubPanelLoading(false);
  };

  const handleCombinedChart = async () => {
    setCombinedChart((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });

    if (!youtubeUrl || subPanelLoading) return;
    setSubPanelLoading(true);
    setEmotionSubPanel(EMOTION_PANEL.combined);
    setEmotionTopicsResult(null);
    setNegativePeakAnalysis(null);
    setCombinedChartError(null);

    setTrendChart((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });

    try {
      const res = await fetch(`${API_BASE}/combined_trend_chart`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: youtubeUrl, time_unit: "hour" }),
      });

      if (!res.ok) throw new Error("無法取得綜合圖表");
      const blob = await res.blob();
      setCombinedChart(URL.createObjectURL(blob));
    } catch (err) {
      setCombinedChartError(err instanceof Error ? err.message : "無法取得綜合圖表");
    }

    setSubPanelLoading(false);
  };

  const stats = payload?.stats;
  const emotions = stats?.emotions;

  return (
    <div className="space-y-4">
      {loading && <p className="text-sm text-white/60">正在產生情緒雷達圖…</p>}
      {loadError && (
        <p className="rounded-xl border border-amber-500/30 bg-amber-950/30 px-4 py-3 text-amber-100">
          {loadError}（若留言已變更或 API 金鑰失效，可能無法重繪）
        </p>
      )}
      {imageSrc && (
        <figure className="overflow-hidden rounded-2xl border border-white/15 bg-black/30 p-4">
          <img
            src={imageSrc}
            alt="情緒雷達圖"
            className="mx-auto max-h-[480px] w-auto max-w-full object-contain"
          />
          <figcaption className="mt-2 text-center text-xs text-white/50">
            {chartFromDb ? "情緒分析雷達圖（資料庫存檔）" : "情緒分析雷達圖"}
          </figcaption>

          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <button
              type="button"
              onClick={handleEmotionTopics}
              disabled={subPanelLoading}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${
                emotionSubPanel === EMOTION_PANEL.topics
                  ? "bg-purple-500"
                  : "bg-purple-600 hover:bg-purple-500"
              }`}
            >
              顯示情緒話題
            </button>
            <button
              type="button"
              onClick={handleTrendChart}
              disabled={subPanelLoading}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${
                emotionSubPanel === EMOTION_PANEL.trend
                  ? "bg-indigo-500"
                  : "bg-indigo-600 hover:bg-indigo-500"
              }`}
            >
              情緒趨勢
            </button>
            <button
              type="button"
              onClick={handleCombinedChart}
              disabled={subPanelLoading}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${
                emotionSubPanel === EMOTION_PANEL.combined
                  ? "bg-pink-500"
                  : "bg-pink-600 hover:bg-pink-500"
              }`}
            >
              綜合圖表
            </button>
          </div>

          {subPanelLoading && <div className="mt-4 text-center text-sm text-white/60">載入中…</div>}

          {emotionSubPanel === EMOTION_PANEL.combined && combinedChartError && (
            <div className="mt-4 rounded-xl border border-red-500/30 bg-red-950/30 p-4 text-sm text-red-100">
              {combinedChartError}
            </div>
          )}

          {emotionSubPanel === EMOTION_PANEL.topics && emotionTopicsResult && (
            <div className="mt-4 rounded-xl border border-white/15 bg-black/30 p-4">
              {emotionTopicsResult.error ? (
                <div className="text-center text-red-400">
                  <p>情緒話題分析失敗</p>
                  <p className="text-sm text-red-300">{emotionTopicsResult.error}</p>
                </div>
              ) : (
                <EmotionTopicGroups result={emotionTopicsResult} />
              )}
            </div>
          )}

          {emotionSubPanel === EMOTION_PANEL.trend && trendChart && (
            <figure className="mt-4 overflow-hidden rounded-xl border border-white/15 bg-black/30 p-3">
              <img
                src={trendChart}
                alt="趨勢圖表"
                className="mx-auto max-h-[320px] w-auto max-w-full object-contain"
              />
              <figcaption className="mt-1 text-center text-xs text-white/50">情緒趨勢分析</figcaption>

              {negativePeakAnalysis && (
                <NegativePeakAnalysisCard analysis={negativePeakAnalysis} />
              )}
            </figure>
          )}

          {emotionSubPanel === EMOTION_PANEL.combined && combinedChart && (
            <figure className="mt-4 overflow-hidden rounded-xl border border-white/15 bg-black/30 p-3">
              <img
                src={combinedChart}
                alt="綜合圖表"
                className="mx-auto max-h-[400px] w-auto max-w-full object-contain"
              />
              <figcaption className="mt-1 text-center text-xs text-white/50">綜合趨勢分析</figcaption>
            </figure>
          )}
        </figure>
      )}

      {(payload?.title || payload?.language != null || emotions) && (
        <article className="rounded-2xl border border-white/15 bg-gray-900/50 p-5 backdrop-blur-md">
          <h3 className="font-semibold text-violet-200">紀錄中的情緒資料</h3>
          {payload?.title && <p className="mt-2 text-white/90">{payload.title}</p>}
          {payload?.language && <p className="mt-1 text-sm text-white/65">主要語言：{payload.language}</p>}
          {typeof payload?.total_comments === "number" && (
            <p className="mt-1 text-sm text-white/65">分析留言數：{payload.total_comments}</p>
          )}
          {emotions && Object.keys(emotions).length > 0 && (
            <ul className="mt-3 grid gap-1 text-sm sm:grid-cols-2">
              {Object.entries(emotions).map(([key, value]) => (
                <li key={key} className="flex justify-between gap-2 rounded-lg bg-black/25 px-3 py-2">
                  <span className="text-white/75">{key}</span>
                  <span className="tabular-nums text-white/90">{value}</span>
                </li>
              ))}
            </ul>
          )}
        </article>
      )}
    </div>
  );
}

function EmotionTopicGroups({ result }) {
  return (
    <>
      <h4 className="mb-3 text-center font-semibold">情緒話題詳細分析</h4>
      <EmotionTopicSection
        title="正面情緒話題"
        titleClassName="text-green-300"
        cardClassName="border-green-500/30 bg-green-950/40"
        tagClassName="bg-green-800/50 text-green-200"
        textClassName="text-green-100"
        labelClassName="text-green-400"
        topics={result.positive_topics}
      />
      <EmotionTopicSection
        title="負面情緒話題"
        titleClassName="text-red-300"
        cardClassName="border-red-500/30 bg-red-950/40"
        tagClassName="bg-red-800/50 text-red-200"
        textClassName="text-red-100"
        labelClassName="text-red-400"
        topics={result.negative_topics}
      />
      <EmotionTopicSection
        title="中立情緒話題"
        titleClassName="text-gray-300"
        cardClassName="border-gray-500/30 bg-gray-950/40"
        tagClassName="bg-gray-800/50 text-gray-200"
        textClassName="text-gray-100"
        labelClassName="text-gray-400"
        topics={result.neutral_topics}
      />
    </>
  );
}

function EmotionTopicSection({
  title,
  titleClassName,
  cardClassName,
  tagClassName,
  textClassName,
  labelClassName,
  topics,
}) {
  if (!topics?.length) return null;

  return (
    <div className="mb-4">
      <h5 className={`mb-2 font-semibold ${titleClassName}`}>{title}</h5>
      <div className="space-y-3">
        {topics.map((topic, index) => (
          <div key={`${topic.topic ?? title}-${index}`} className={`rounded-lg border p-3 ${cardClassName}`}>
            <div className="mb-2 flex items-start justify-between">
              <h6 className={`font-medium ${textClassName}`}>{topic.topic}</h6>
              <span className={`text-sm ${titleClassName}`}>{topic.count} 則留言</span>
            </div>
            {topic.keywords?.length > 0 && (
              <div className="mb-2">
                <p className={`mb-1 text-xs ${labelClassName}`}>關鍵字：</p>
                <div className="flex flex-wrap gap-1">
                  {topic.keywords.map((keyword, keywordIndex) => (
                    <span key={`${keyword}-${keywordIndex}`} className={`rounded px-2 py-1 text-xs ${tagClassName}`}>
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {topic.summary && (
              <div className="mb-2">
                <p className={`mb-1 text-xs ${labelClassName}`}>摘要：</p>
                <p className={`text-xs leading-relaxed ${textClassName}`}>{topic.summary}</p>
              </div>
            )}
            {topic.comments?.length > 0 && (
              <div>
                <p className={`mb-1 text-xs ${labelClassName}`}>代表留言：</p>
                <div className="space-y-1">
                  {topic.comments.map((comment, commentIndex) => (
                    <p key={`${commentIndex}-${comment.slice(0, 12)}`} className={`text-xs italic ${textClassName}`}>
                      {"\""}{comment}{"\""}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function NegativePeakAnalysisCard({ analysis }) {
  const peakTimeLabel = analysis?.peak_time
    ? new Date(analysis.peak_time).toLocaleString()
    : "未知";

  const peakSentimentLabel =
    typeof analysis?.peak_sentiment === "number"
      ? analysis.peak_sentiment.toFixed(2)
      : "未知";

  return (
    <div className="mt-4 rounded-xl border border-red-500/30 bg-red-950/40 p-4">
      {analysis.error ? (
        <div className="text-center text-red-400">
          <p>負面情緒高峰分析失敗</p>
          <p className="text-sm text-red-300">{analysis.error}</p>
        </div>
      ) : (
        <>
          <h4 className="mb-3 font-semibold text-red-300">負面情緒高峰詳細分析</h4>
          <div className="mb-4 grid grid-cols-2 gap-4">
            <div>
              <p className="mb-1 text-xs text-red-400">高峰時間：</p>
              <p className="text-sm text-red-100">{peakTimeLabel}</p>
            </div>
            <div>
              <p className="mb-1 text-xs text-red-400">情緒分數：</p>
              <p className="text-sm font-bold text-red-100">{peakSentimentLabel}</p>
            </div>
          </div>

          {analysis.negative_emotions && (
            <div className="mb-4">
              <p className="mb-2 text-xs text-red-400">負面情緒分布：</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(analysis.negative_emotions).map(([emotion, count]) => (
                  <span key={emotion} className="rounded-full bg-red-800/50 px-3 py-1 text-xs text-red-200">
                    {emotion}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}

          {analysis.peak_keywords?.length > 0 && (
            <div className="mb-4">
              <p className="mb-2 text-xs text-red-400">高峰關鍵字：</p>
              <div className="flex flex-wrap gap-1">
                {analysis.peak_keywords.map((keyword, index) => (
                  <span key={`${keyword}-${index}`} className="rounded bg-red-800/30 px-2 py-1 text-xs text-red-200">
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          )}

          {analysis.peak_summary && (
            <div className="mb-4">
              <p className="mb-2 text-xs text-red-400">高峰摘要：</p>
              <p className="text-xs leading-relaxed text-red-200">{analysis.peak_summary}</p>
            </div>
          )}

          {analysis.peak_comments?.length > 0 && (
            <div>
              <p className="mb-2 text-xs text-red-400">
                高峰留言 ({analysis.total_peak_comments} 則)：
              </p>
              <div className="space-y-2">
                {analysis.peak_comments.map((comment, index) => (
                  <p key={`${index}-${comment.slice(0, 12)}`} className="rounded bg-red-900/20 p-2 text-xs italic text-red-100">
                    {"\""}{comment}{"\""}
                  </p>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
