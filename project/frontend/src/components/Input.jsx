"use client";

export function Input({ text, loading, activeAction, onTextChange, onSubmit }) {
  const createClickHandler = (action) => () => onSubmit(action);
  const actions = [
    { action: "analyze", label: "綜合分析", description: "整體", activeTone: "from-indigo-500 to-sky-500", accent: "bg-indigo-300" },
    { action: "summary", label: "留言摘要", description: "重點", activeTone: "from-violet-500 to-fuchsia-500", accent: "bg-violet-300" },
    { action: "keyword", label: "熱門關鍵詞", description: "詞頻", activeTone: "from-amber-500 to-orange-500", accent: "bg-amber-300" },
    { action: "topics", label: "熱門主題", description: "群集", activeTone: "from-sky-500 to-blue-500", accent: "bg-sky-300" },
    { action: "emotion", label: "情緒風向", description: "傾向", activeTone: "from-rose-500 to-pink-500", accent: "bg-rose-300" },
    { action: "criticism", label: "批評回饋", description: "問題", activeTone: "from-red-500 to-rose-500", accent: "bg-red-300" },
    { action: "timeline", label: "時間軸熱點", description: "脈絡", activeTone: "from-cyan-500 to-teal-500", accent: "bg-cyan-300" },
    { action: "videoContent", label: "影片內容脈絡", description: "章節", activeTone: "from-emerald-500 to-green-500", accent: "bg-emerald-300" },
  ];

  return (
    <div className="rounded-2xl border border-white/15 bg-white/6 p-5 backdrop-blur-md">
      <label className="block text-sm font-medium text-white/85">
        貼上 YouTube 影片連結開始分析
      </label>
      <div className="mt-3 space-y-3">
        <input
          type="url"
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          className="min-h-[48px] w-full rounded-xl border border-white/20 bg-white/10 px-4 text-white outline-none placeholder:text-white/45 focus:ring-2 focus:ring-indigo-400"
          placeholder="YouTube 影片網址"
        />
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
          {actions.map(({ action, label, description, activeTone, accent }) => {
            const isActive = activeAction === action;
            const buttonClassName = isActive
              ? `border-white/70 bg-gradient-to-br ${activeTone} text-white shadow-xl shadow-black/30 ring-2 ring-white/75 ring-offset-2 ring-offset-slate-950`
              : "border-white/15 bg-white/7 text-white/78 hover:border-white/35 hover:bg-white/12 hover:text-white";

            return (
              <button
                key={action}
                type="button"
                onClick={createClickHandler(action)}
                disabled={loading}
                aria-pressed={isActive}
                className={`group relative min-h-[62px] overflow-hidden rounded-xl border px-3 py-2 text-left transition duration-200 hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-white/45 disabled:cursor-not-allowed disabled:translate-y-0 disabled:opacity-70 ${buttonClassName}`}
              >
                {!isActive && <span className={`absolute inset-x-3 top-0 h-0.5 rounded-full opacity-60 ${accent}`} />}
                {isActive && <span className="absolute inset-x-0 top-0 h-1 bg-white/90" />}
                <span className="relative block text-sm font-semibold leading-5">{label}</span>
                <span className={`relative mt-0.5 block text-xs leading-4 transition ${isActive ? "text-white/90" : "text-white/50 group-hover:text-white/75"}`}>
                  {isActive ? (loading ? "執行中" : "已選取") : description}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
