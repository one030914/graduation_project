"use client";

import { OpinionGauge } from "@/components/charts/OpinionGauge";
import { EmotionRadarChart } from "@/components/charts/EmotionRadarChart";
import { FallbackText, InfoTile, ResultFooter } from "@/components/results/ResultCards";

const EMOTION_LABELS = {
  Joy: "喜悅",
  Angry: "憤怒",
  Sad: "悲傷",
  Disgusted: "厭惡",
  Surprised: "驚訝",
  Fearful: "恐懼",
  Neutral: "中性",
};

function fmtPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

function getEmotionLabel(key) {
  return EMOTION_LABELS[key] || key || "未知";
}

function TextCard({ title, children, tone = "indigo" }) {
  const titleClass = tone === "amber" ? "text-amber-200" : "text-indigo-200";

  return (
    <section className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-6 text-white shadow-[0_18px_48px_rgba(2,6,23,0.3)] ring-1 ring-indigo-300/5 backdrop-blur-md">
      <h3 className={`text-lg font-black tracking-normal ${titleClass}`}>{title}</h3>
      <div className="mt-4 text-sm font-semibold leading-7 text-white/72">{children}</div>
    </section>
  );
}

function SentimentRatioCards({ positive = 0, neutral = 0, negative = 0 }) {
  const items = [
    {
      label: "正向比例",
      value: positive,
      className: "border-emerald-300/15 bg-emerald-400/8 text-emerald-200",
    },
    {
      label: "中性比例",
      value: neutral,
      className: "border-slate-300/15 bg-slate-400/8 text-slate-200",
    },
    {
      label: "負向比例",
      value: negative,
      className: "border-rose-300/15 bg-rose-400/8 text-rose-200",
    },
  ];

  return (
    <section className="grid gap-4 sm:grid-cols-3">
      {items.map((item) => (
        <div
          key={item.label}
          className={`rounded-2xl border p-5 shadow-[0_18px_48px_rgba(2,6,23,0.22)] ring-1 ring-white/5 ${item.className}`}
        >
          <p className="text-sm font-black text-white/50">{item.label}</p>
          <p className="mt-2 text-3xl font-black">{fmtPercent(item.value)}</p>

          <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-current"
              style={{
                width: `${Math.max(6, Math.min(100, Number(item.value) * 100))}%`,
              }}
            />
          </div>
        </div>
      ))}
    </section>
  );
}

function EmotionDistributionList({ data = [] }) {
  const rawChartData = data
    .map((item, index) => {
      const rawName = item.key || item.label || item.emotion || item.name || `emotion-${index}`;
      const count = Number(item.count ?? item.total ?? 0);
      const rawRatio = Number(item.ratio ?? item.percent ?? item.value ?? 0);
      const providedRatio = rawRatio > 1 ? rawRatio / 100 : rawRatio;

      return {
        name: getEmotionLabel(rawName),
        count,
        providedRatio,
      };
    })
    .filter((item) => item.count > 0 || item.providedRatio > 0);

  if (rawChartData.length === 0) {
    return (
      <TextCard title="情緒分布明細">
        <FallbackText>目前沒有情緒分布明細資料。</FallbackText>
      </TextCard>
    );
  }

  const totalCount = rawChartData.reduce((sum, item) => sum + item.count, 0);
  const chartData = rawChartData
    .map((item) => ({
      ...item,
      ratio: item.providedRatio > 0 ? item.providedRatio : item.count / Math.max(totalCount, 1),
    }))
    .sort((a, b) => b.count - a.count);

  return (
    <TextCard title="情緒分布明細">
      <div className="space-y-3">
        {chartData.map((item) => {
          const width = item.ratio * 100;

          return (
            <div key={item.name}>
              <div className="mb-2 flex items-center justify-between gap-3 text-sm font-black">
                <span className="text-white/88">{item.name}</span>
                <span className="text-white/48">
                  {item.count} 則 / {fmtPercent(item.ratio)}
                </span>
              </div>

              <div className="h-2.5 overflow-hidden rounded-full bg-slate-800/80 ring-1 ring-white/5">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-indigo-400 to-violet-400"
                  style={{ width: `${Math.max(6, Math.min(100, width))}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </TextCard>
  );
}

function RepresentativeComments({ commentsByEmotion = {} }) {
  const entries = Object.entries(commentsByEmotion || {})
    .map(([emotion, comments]) => ({
      emotion,
      label: getEmotionLabel(emotion),
      comments: Array.isArray(comments) ? comments : [],
    }))
    .filter((item) => item.comments.length > 0)
    .slice(0, 4);

  if (entries.length === 0) {
    return (
      <TextCard title="各情緒代表留言">
        <FallbackText>目前沒有各情緒代表留言資料。</FallbackText>
      </TextCard>
    );
  }

  return (
    <TextCard title="各情緒代表留言">
      <div className="space-y-5">
        {entries.map((group) => (
          <section
            key={group.emotion}
            className="rounded-xl border border-white/10 bg-white/[0.04] p-4"
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <h4 className="font-black text-indigo-100">{group.label}</h4>
              <span className="rounded-full bg-indigo-400/10 px-2.5 py-1 text-xs font-black text-indigo-200">
                {group.comments.length} 則
              </span>
            </div>

            <div className="space-y-2">
              {group.comments.slice(0, 3).map((comment, index) => {
                const text =
                  typeof comment === "string"
                    ? comment
                    : comment.text || comment.comment || comment.content || "";

                const likeCount =
                  typeof comment === "object"
                    ? (comment.like_count ?? comment.likes ?? null)
                    : null;

                return (
                  <div
                    key={`${group.emotion}-${index}`}
                    className="border-l-2 border-indigo-300/35 bg-slate-900/50 px-4 py-3"
                  >
                    <p className="text-sm font-semibold leading-7 text-white/76">
                      {text || "無留言內容"}
                    </p>
                    {likeCount !== null && (
                      <p className="mt-1 text-xs font-bold text-white/38">👍 {likeCount}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </TextCard>
  );
}

export function EmotionRecordView({ result }) {
  if (!result) return null;

  if (result.error || result.status === "error") {
    return (
      <p className="rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-100">
        {result.error || result.message || "情緒分析失敗"}
      </p>
    );
  }

  const dominantEmotion =
    result.dominant_emotion?.display_name ||
    result.dominant_emotion?.label ||
    getEmotionLabel(result.dominant_emotion?.emotion) ||
    "未知";

  const chartData = result.chart_data ?? result.radar_data ?? [];
  const representativeComments = result.representative_comments ?? {};

  return (
    <article className="rounded-3xl border border-white/10 bg-slate-950/35 p-5 shadow-[0_24px_70px_rgba(2,6,23,0.32)] ring-1 ring-indigo-300/5 backdrop-blur-md sm:p-7">
      <div className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-6 shadow-[0_18px_48px_rgba(2,6,23,0.28)]">
        <p className="text-xs font-black uppercase tracking-[0.18em] text-indigo-200/70">
          Emotion Analysis
        </p>
        <h2 className="mt-2 text-2xl font-black leading-tight tracking-normal text-white">
          情緒風向分析
        </h2>
        <p className="mt-2 text-sm font-semibold text-white/50">
          {result.title || result.url || "YouTube 留言情緒分析"}
        </p>
      </div>

      <div className="mt-6 space-y-5">
        <TextCard title="分析概況">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <InfoTile
              label="分析留言數"
              value={`${result.analyzed_comments ?? 0} / ${result.total_comments ?? 0}`}
            />
            <InfoTile label="略過留言數" value={result.skipped_comments ?? 0} />
            <InfoTile label="主導情緒" value={dominantEmotion} />
            <InfoTile label="主要語言" value={result.language || "mixed"} />
          </div>

          {result.message && (
            <p className="mt-4 rounded-xl border border-amber-300/20 bg-amber-400/10 px-4 py-3 text-amber-100">
              {result.message}
            </p>
          )}
        </TextCard>

        <div className="grid gap-4 lg:grid-cols-2">
          <OpinionGauge
            score={result.opinion_score ?? 50}
            label={result.opinion_label ?? "中性 / 意見分歧"}
          />

          <TextCard title="風向摘要">
            <p>
              目前留言區整體風向為{" "}
              <span className="font-black text-indigo-100">
                {result.opinion_label || "中性 / 意見分歧"}
              </span>
              ，主導情緒為 <span className="font-black text-indigo-100">{dominantEmotion}</span>。
            </p>
            <p className="mt-3 text-white/58">
              此分數由正向、中性與負向情緒比例綜合計算，適合用來快速判斷留言區整體氣氛。
            </p>
          </TextCard>
        </div>

        <SentimentRatioCards
          positive={result.positive_ratio ?? 0}
          neutral={result.neutral_ratio ?? 0}
          negative={result.negative_ratio ?? 0}
        />

        {chartData.length > 0 ? (
          <EmotionRadarChart data={chartData} />
        ) : (
          <TextCard title="情緒心理圖譜">
            <FallbackText>目前沒有可繪製的情緒圖表資料。</FallbackText>
          </TextCard>
        )}

        <EmotionDistributionList data={chartData} />

        <RepresentativeComments commentsByEmotion={representativeComments} />

        <ResultFooter>
          Emotion：統計留言中的情緒類型、整體風向與代表留言。情緒分類結果會受留言語言、諷刺語氣與上下文影響。
        </ResultFooter>
      </div>
    </article>
  );
}
