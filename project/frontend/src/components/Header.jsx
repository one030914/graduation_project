"use client";

import Link from "next/link";

export function Header({
  showAction = true,
}) {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/10 bg-slate-950/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-3xl font-bold tracking-tight transition hover:text-indigo-200 sm:text-4xl"
          >
            YouTube 留言分析平台
          </Link>
          <p className="mt-2 max-w-xl text-sm text-white/70">留言摘要、關鍵字、主題與情緒視覺化</p>
        </div>
        {showAction && (
          <Link
            href="/history"
            className="inline-flex shrink-0 items-center justify-center rounded-xl bg-white/10 px-5 py-2.5 text-sm font-medium ring-1 ring-white/20 transition hover:bg-white/20"
          >
            歷史紀錄
          </Link>
        )}
      </div>
    </header>
  );
}
