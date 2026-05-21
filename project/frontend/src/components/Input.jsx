"use client";

export function Input({
  text,
  loading,
  onTextChange,
  onSubmit,
}) {
  const createClickHandler = (action) => () => onSubmit(action);

  return (
    <div className="rounded-2xl border border-white/15 bg-white/6 p-5 backdrop-blur-md">
      <label className="block text-sm font-medium text-white/85">
        貼上 YouTube 影片連結開始分析
      </label>
      <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-stretch">
        <input
          type="url"
          value={text}
          onChange={(e) => onTextChange(e.target.value)}
          className="min-h-[48px] flex-1 rounded-xl border border-white/20 bg-white/10 px-4 text-white outline-none placeholder:text-white/45 focus:ring-2 focus:ring-indigo-400"
          placeholder="YouTube 影片網址"
        />
        <div className="flex flex-wrap gap-2 lg:shrink-0">
          <button
            type="button"
            onClick={createClickHandler("analyze")}
            disabled={loading}
            className="min-h-[48px] rounded-xl bg-indigo-500 px-5 font-medium transition hover:bg-indigo-400 disabled:opacity-50"
          >
            留言分析
          </button>
          <button
            type="button"
            onClick={createClickHandler("topics")}
            disabled={loading}
            className="min-h-[48px] rounded-xl bg-sky-600 px-5 font-medium transition hover:bg-sky-500 disabled:opacity-50"
          >
            主題分析
          </button>
          <button
            type="button"
            onClick={createClickHandler("videoContent")}
            disabled={loading}
            className="min-h-[48px] rounded-xl bg-emerald-600 px-5 font-medium transition hover:bg-emerald-500 disabled:opacity-50"
          >
            影片內容
          </button>
        </div>
      </div>
    </div>
  );
}
