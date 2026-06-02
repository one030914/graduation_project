"use client";

import { useState } from "react";
import { clip } from "@/lib/analysisFormat";
import { FallbackText, InfoTile, ResultCard, ResultFooter, ResultShell } from "@/components/results/ResultCards";

function formatSource(source) {
  if (source === "caption") return "手動 CC 字幕";
  if (source === "whisper") return "Whisper 逐字稿";
  return "未知";
}

function formatCount(value) {
  const count = Number(value);
  if (!Number.isFinite(count) || count <= 0) return null;
  return new Intl.NumberFormat("zh-TW").format(Math.round(count));
}

function formatTimestamp(seconds) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const secs = value % 60;
  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }
  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function buildTimestampUrl(url, seconds) {
  if (!url) return null;
  try {
    const nextUrl = new URL(url);
    nextUrl.searchParams.set("t", `${Math.max(0, Math.floor(Number(seconds) || 0))}s`);
    return nextUrl.toString();
  } catch {
    return null;
  }
}

function getImportanceLabel(importance) {
  if (importance === "high") return "高重點";
  if (importance === "low") return "低重點";
  return "中重點";
}

function getImportanceClassName(importance) {
  if (importance === "high") return "bg-red-400/12 text-red-100 ring-red-300/25";
  if (importance === "low") return "bg-slate-400/10 text-slate-200 ring-slate-300/20";
  return "bg-amber-400/12 text-amber-100 ring-amber-300/25";
}

function getQualityNote(source) {
  if (source === "whisper") {
    return "此逐字稿由 Whisper 自動辨識產生，可能包含誤聽、漏字或斷句不自然。";
  }
  if (source === "caption") {
    return "此逐字稿來自 YouTube 字幕，品質通常較穩定，但仍可能受字幕斷句與原始字幕品質影響。";
  }
  return "逐字稿來源未知，分析結果可能受原始逐字稿品質影響。";
}

export function VideoContentResultView({ result }) {
  const [chapterQuery, setChapterQuery] = useState("");

  const safeResult = result ?? {};
  const legacySummary =
    safeResult.summary_zh?.length > 0 ? safeResult.summary_zh : safeResult.summary_en;
  const summaryText = String(safeResult.summary_text || legacySummary?.join(" ") || "").trim();
  const finalConclusion = String(safeResult.final_conclusion || "").trim();
  const recommendedAudience = String(safeResult.recommended_audience || "").trim();
  const actionSuggestions = Array.isArray(safeResult.action_suggestions)
    ? safeResult.action_suggestions
    : [];
  const transcriptWordCount = formatCount(safeResult.transcript_word_count);
  const chapters = Array.isArray(safeResult.chapter_timeline) ? safeResult.chapter_timeline : [];
  const normalizedChapterQuery = chapterQuery.trim().toLowerCase();
  const filteredChapters = normalizedChapterQuery
    ? chapters.filter((chapter) => {
        const haystack = [
          chapter.title,
          chapter.summary,
          chapter.importance,
          ...(Array.isArray(chapter.keywords) ? chapter.keywords : []),
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalizedChapterQuery);
      })
    : chapters;

  if (!result) return null;

  if (safeResult.error) {
    return (
      <p className="rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-100">
        {safeResult.error}
      </p>
    );
  }

  return (
    <ResultShell label="Video Content" title={clip(safeResult.title || "影片內容分析", 256)}>
      <ResultCard title="逐字稿資訊" tone="emerald">
        <div className="grid gap-3 sm:grid-cols-3">
          <InfoTile
            label="逐字稿來源"
            value={formatSource(safeResult.transcript_source)}
            tone="emerald"
          />
          <InfoTile label="語言" value={safeResult.language || "未知"} />
          <InfoTile label="逐字稿總字數" value={transcriptWordCount || "無資料"} />
        </div>
      </ResultCard>
      <ResultCard title="摘要" tone="emerald">
        {summaryText ? <p>{summaryText}</p> : <FallbackText>目前沒有影片內容摘要資料。</FallbackText>}
      </ResultCard>

      <ResultCard title="結論與行動建議" tone="emerald">
        {finalConclusion || recommendedAudience || actionSuggestions.length > 0 ? (
          <div className="space-y-3">
            {finalConclusion ? <p>{finalConclusion}</p> : <FallbackText>目前沒有結論資料。</FallbackText>}
            {recommendedAudience ? (
              <p>
                <span className="font-black text-white">適合對象：</span>
                {recommendedAudience}
              </p>
            ) : (
              <FallbackText>目前沒有適合對象資料。</FallbackText>
            )}
            {actionSuggestions.length > 0 ? (
              <ul className="list-disc space-y-1 pl-5">
                {actionSuggestions.slice(0, 5).map((item, index) => (
                  <li key={`${item}-${index}`}>{clip(item, 180)}</li>
                ))}
              </ul>
            ) : (
              <FallbackText>目前沒有行動建議資料。</FallbackText>
            )}
          </div>
        ) : (
          <FallbackText>目前沒有結論與行動建議資料。</FallbackText>
        )}
      </ResultCard>

      <ResultCard title="逐字稿品質提示" tone="emerald">
        <p>
          {getQualityNote(safeResult.transcript_source)}
          {transcriptWordCount ? ` 目前可讀字數約 ${transcriptWordCount}。` : ""}
        </p>
      </ResultCard>

      <section className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-6 text-white shadow-[0_18px_48px_rgba(2,6,23,0.3)] ring-1 ring-indigo-300/5 backdrop-blur-md">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <h3 className="text-lg font-black tracking-normal text-emerald-200">章節時間軸</h3>
              <p className="mt-1 text-base font-semibold text-white/45">
                共 {chapters.length} 個章節{filteredChapters.length !== chapters.length ? `，顯示 ${filteredChapters.length} 個` : ""}
              </p>
            </div>
            {chapters.length > 0 && (
              <label className="w-full md:max-w-xs">
              <span className="sr-only">搜尋章節或關鍵字</span>
              <input
                type="search"
                value={chapterQuery}
                onChange={(event) => setChapterQuery(event.target.value)}
                className="min-h-10 w-full rounded-xl border border-white/15 bg-white/8 px-3 text-base text-white outline-none placeholder:text-white/40 focus:ring-2 focus:ring-emerald-300/50"
                placeholder="搜尋章節或關鍵字"
              />
              </label>
            )}
          </div>
          <div className="mt-4 space-y-3">
              {chapters.length === 0 && <FallbackText>目前沒有章節時間軸資料。</FallbackText>}
              {chapters.length > 0 && filteredChapters.map((chapter, index) => {
                const start = Number(chapter.start_seconds) || 0;
                const end = Number(chapter.end_seconds) || 0;
                const timestampUrl = buildTimestampUrl(safeResult.url, start);
                const timeLabel = `${formatTimestamp(start)} - ${formatTimestamp(end)}`;
                const chapterKey = `${chapter.start_seconds}-${chapter.end_seconds}-${index}`;

                return (
                  <div
                    key={chapterKey}
                    className="border-l-4 border-emerald-400/70 bg-slate-950/45 px-4 py-3 ring-1 ring-white/10"
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          {timestampUrl ? (
                            <a
                              href={timestampUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="text-base font-medium text-emerald-200 transition hover:text-emerald-100"
                            >
                              {timeLabel}
                            </a>
                          ) : (
                            <p className="text-base font-medium text-emerald-200">{timeLabel}</p>
                          )}
                          <span
                            className={`px-2 py-1 text-base font-medium ring-1 ${getImportanceClassName(chapter.importance)}`}
                          >
                            {getImportanceLabel(chapter.importance)}
                          </span>
                        </div>
                        <h4 className="mt-1 font-semibold text-white">
                          {clip(chapter.title || "重點片段", 120)}
                        </h4>
                      </div>
                      {timestampUrl ? (
                        <a
                          href={timestampUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex min-h-8 items-center justify-center border border-white/15 bg-white/8 px-3 text-base font-medium text-white/80 transition hover:border-emerald-300/45 hover:bg-emerald-400/12 hover:text-emerald-100 focus:outline-none focus:ring-2 focus:ring-emerald-300/50"
                        >
                          前往時間點
                        </a>
                      ) : (
                        <span className="inline-flex min-h-8 items-center justify-center border border-white/10 bg-white/5 px-3 text-base font-medium text-white/35">
                          無法跳轉
                        </span>
                      )}
                    </div>
                    {chapter.summary && (
                      <p className="mt-2 leading-6 text-white/80">{clip(chapter.summary, 500)}</p>
                    )}
                    {Array.isArray(chapter.keywords) && chapter.keywords.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {chapter.keywords.slice(0, 5).map((keyword, keywordIndex) => (
                          <span
                            key={`${keyword}-${keywordIndex}`}
                            className="bg-emerald-400/10 px-2 py-1 text-base font-medium text-emerald-100 ring-1 ring-emerald-300/20"
                          >
                            {clip(keyword, 32)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
              {chapters.length > 0 && filteredChapters.length === 0 && (
                <p className="border border-white/10 bg-slate-950/35 px-4 py-3 text-base text-white/65">
                  沒有符合搜尋條件的章節。
                </p>
              )}
          </div>
        </section>

      <ResultFooter>
        Video Content：根據 YouTube 字幕或 Whisper 逐字稿整理影片摘要、章節與建議。
        逐字稿來源與品質會影響內容判讀，長影片可能需要較久時間完成分析。
      </ResultFooter>
    </ResultShell>
  );
}
