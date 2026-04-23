"use client";

import { clip, fmtKeywords, fmtList } from "@/lib/analysisFormat";

function formatSource(source) {
  if (source === "caption") return "手動 CC 字幕";
  if (source === "whisper") return "Whisper 逐字稿";
  return "未知";
}

export function VideoContentResultView({ result }) {
  if (!result) return null;

  if (result.error) {
    return (
      <p className="rounded-xl border border-red-500/30 bg-red-950/40 px-4 py-3 text-red-100">
        {result.error}
      </p>
    );
  }

  const summary = result.summary_zh?.length > 0 ? result.summary_zh : result.summary_en;
  const keywords = result.keywords_zh?.length > 0 ? result.keywords_zh : result.keywords_en;

  return (
    <article className="rounded-2xl border border-white/15 bg-gray-900/50 p-6 shadow-inner backdrop-blur-md">
      <h2 className="text-xl font-bold">{clip(result.title || "影片內容分析", 256)}</h2>

      <div className="mt-3 flex flex-wrap gap-3 text-sm text-white/65">
        <span>逐字稿來源：{formatSource(result.transcript_source)}</span>
        {result.language && <span>語言：{result.language}</span>}
      </div>

      <div className="mt-6 space-y-5">
        {summary?.length > 0 && (
          <section>
            <h3 className="font-semibold text-emerald-200">摘要</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(summary)}</p>
          </section>
        )}

        {keywords?.length > 0 && (
          <section>
            <h3 className="font-semibold text-emerald-200">關鍵字</h3>
            <p className="mt-2 text-white/90">{fmtKeywords(keywords)}</p>
          </section>
        )}

        {result.highlights?.length > 0 && (
          <section>
            <h3 className="font-semibold text-emerald-200">代表片段</h3>
            <p className="mt-2 whitespace-pre-line text-white/90">{fmtList(result.highlights, 5)}</p>
          </section>
        )}
      </div>
    </article>
  );
}
