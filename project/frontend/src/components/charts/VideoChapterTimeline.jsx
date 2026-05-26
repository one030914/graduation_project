"use client";

function formatTime(seconds) {
  const value = Number(seconds) || 0;
  const h = Math.floor(value / 3600);
  const m = Math.floor((value % 3600) / 60);
  const s = Math.floor(value % 60);

  if (h > 0) {
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  return `${m}:${String(s).padStart(2, "0")}`;
}

function importanceLabel(value) {
  const map = {
    high: "高",
    medium: "中",
    low: "低",
  };

  return map[value] || value || "未知";
}

export function VideoChapterTimeline({ chapters = [] }) {
  const items = chapters
    .map((chapter, index) => ({
      title: chapter.title || `章節 ${index + 1}`,
      summary: chapter.summary || "",
      start: Number(chapter.start_seconds ?? 0),
      end: Number(chapter.end_seconds ?? 0),
      keywords: chapter.keywords ?? [],
      importance: chapter.importance || "medium",
    }))
    .slice(0, 8);

  if (items.length === 0) return null;

  return (
    <section className="rounded-2xl border border-white/10 bg-black/20 p-6">
      <div>
        <h3 className="font-semibold text-indigo-200">影片內容脈絡</h3>
        <p className="mt-1 text-sm text-white/45">根據字幕分析影片章節，協助解讀留言討論背景</p>
      </div>

      <div className="mt-5 space-y-3">
        {items.map((chapter, index) => (
          <div
            key={`${chapter.start}-${chapter.title}-${index}`}
            className="rounded-xl border border-white/10 bg-white/5 p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm text-white/45">
                  {formatTime(chapter.start)} - {formatTime(chapter.end)}
                </p>
                <h4 className="mt-1 font-semibold text-white">{chapter.title}</h4>
              </div>

              <span className="rounded-full bg-indigo-500/20 px-3 py-1 text-xs text-indigo-100">
                重要度：{importanceLabel(chapter.importance)}
              </span>
            </div>

            {chapter.summary && (
              <p className="mt-3 text-sm leading-6 text-white/75">{chapter.summary}</p>
            )}

            {chapter.keywords.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {chapter.keywords.slice(0, 6).map((keyword) => (
                  <span
                    key={keyword}
                    className="rounded-full bg-white/8 px-2.5 py-1 text-xs text-white/65"
                  >
                    #{keyword}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
