"use client";

import { useEffect, useState } from "react";
import { HistoryRecordBody } from "@/lib/ResultViews";
import { Header } from "@/components/Header";

const CATEGORIES = [
  { value: "分析", label: "分析" },
  { value: "摘要", label: "摘要" },
  { value: "關鍵詞", label: "關鍵詞" },
  { value: "主題", label: "主題" },
  { value: "情緒", label: "情緒" },
  { value: "批評", label: "批評" },
  { value: "時間軸", label: "時間軸" },
  { value: "影片內容", label: "影片內容" },
];

function formatWhen(record) {
  const raw = record.analysis_date ?? record.date;
  if (!raw) return "—";
  try {
    return new Date(raw).toLocaleString("zh-TW");
  } catch {
    return String(raw);
  }
}

export default function History() {
  const [records, setRecords] = useState(null);
  const [categories, setCategories] = useState([]);
  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [error, setError] = useState(null);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadRecords() {
      try {
        const params = new URLSearchParams();
        for (const value of categories) {
          params.append("category", value);
        }
        if (appliedSearch?.trim()) params.set("q", appliedSearch.trim());
        const qs = params.toString();
        const res = await fetch(`/api/history${qs ? `?${qs}` : ""}`);
        const data = await res.json();

        if (cancelled) return;

        if (!res.ok) {
          setError(data.error || "載入失敗");
          setRecords([]);
          return;
        }

        setError(null);
        setRecords(data.records || []);
      } catch {
        if (cancelled) return;
        setError("無法連線到伺服器");
        setRecords([]);
      }
    }

    void loadRecords();

    return () => {
      cancelled = true;
    };
  }, [categories, appliedSearch, reloadKey]);

  const runSearch = () => {
    const nextSearch = searchInput;
    setRecords(null);
    setError(null);
    setAppliedSearch(nextSearch);
    if (nextSearch === appliedSearch) {
      setReloadKey((value) => value + 1);
    }
  };

  const handleCategoryToggle = (value) => {
    setRecords(null);
    setError(null);
    setCategories((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    );
  };
  

  const loading = records === null;

  return (
    <div className="min-h-screen text-white">
      <Header
        showAction={false}
      />

      <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
        <h1 className="text-3xl font-bold">歷史紀錄</h1>

        <div className="flex flex-col gap-2 rounded-2xl border border-white/15 bg-white/6 p-5 backdrop-blur-md lg:flex-row lg:items-stretch">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && runSearch()}
              placeholder="搜尋分析紀錄"
              className="min-h-[48px] flex-1 rounded-xl border border-white/20 bg-white/10 px-4 text-white outline-none placeholder:text-white/45 focus:ring-2 focus:ring-indigo-400"
            />
            <button
              type="button"
              onClick={runSearch}
              className="min-h-[48px] rounded-xl bg-indigo-500 px-5 font-medium transition hover:bg-indigo-400"
            >
              搜尋
            </button>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className="self-center text-sm text-white/70">類型</span>
          {CATEGORIES.map((c) => {
            const active = categories.includes(c.value);

            return (
              <button
                key={c.value}
                type="button"
                onClick={() => handleCategoryToggle(c.value)}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                  active
                    ? "bg-indigo-500 text-white"
                    : "bg-white/10 text-white/90 ring-1 ring-white/20 hover:bg-white/20"
                }`}
              >
                {c.label}
              </button>
            );
          })}
        </div>

        {error && <p className="rounded-lg bg-red-500/20 px-3 py-2 text-red-100">{error}</p>}

        {loading ? (
          <p className="text-white/80">載入中…</p>
        ) : (
          <div className="space-y-3">
            {records.length === 0 && !error && <p className="text-white/70">沒有紀錄</p>}
            {records.map((item) => (
              <div
                key={item.id}
                className="flex flex-col gap-2 rounded-xl bg-gray-900/90 p-4 ring-1 ring-white/10 transition hover:bg-gray-800/90 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold">{item.title || "（無標題）"}</p>
                  <p className="truncate text-sm text-gray-400">{item.youtube_url}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    {item.category} · {formatWhen(item)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setDetail(item)}
                  className="shrink-0 text-blue-400 hover:underline"
                >
                  查看
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      {detail && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => setDetail(null)}
        >
          <div
            className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-gray-950/95 p-6 text-left shadow-xl ring-1 ring-white/20"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-6 flex items-start justify-between gap-4 border-b border-white/10 pb-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-indigo-300/90">
                  與首頁相同預覽
                </p>
                <h2 className="mt-1 text-lg font-bold text-white">{detail.title || "紀錄詳情"}</h2>
                <p className="mt-1 break-all text-sm text-gray-400">{detail.youtube_url}</p>
                <p className="mt-2 text-xs text-gray-500">
                  {detail.category} · {formatWhen(detail)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setDetail(null)}
                className="rounded-lg bg-white/10 px-3 py-1.5 text-sm hover:bg-white/20"
              >
                關閉
              </button>
            </div>
            <HistoryRecordBody
              category={detail.category}
              payload={detail.payload}
              youtubeUrl={detail.youtube_url}
            />
          </div>
        </div>
      )}
    </div>
  );
}
