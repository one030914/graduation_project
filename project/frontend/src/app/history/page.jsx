"use client";

import { useEffect, useState } from "react";
import { HistoryRecordBody } from "@/lib/ResultViews";
import { Header } from "@/components/Header";

const CATEGORIES = [
  { value: "analyze", label: "綜合分析" },
  { value: "topics", label: "熱門主題" },
  { value: "emotion", label: "情緒風向" },
  { value: "timeline", label: "時間軸熱點" },
  { value: "video_content", label: "影片內容脈絡" },
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

async function readApiResponse(res) {
  const text = await res.text();

  if (!text) return {};

  try {
    return JSON.parse(text);
  } catch {
    return {
      error: `API 回傳非 JSON（HTTP ${res.status}）：${text.slice(0, 180)}`,
    };
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
  const [deletingId, setDeletingId] = useState(null);

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
        const data = await readApiResponse(res);

        if (cancelled) return;

        if (!res.ok) {
          setError(data.error || `載入失敗（HTTP ${res.status}）`);
          setRecords([]);
          return;
        }

        setError(null);
        setRecords(data.records || []);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "無法連線到伺服器");
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
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value],
    );
  };

  const openDetail = (item) => {
    setDetail(item);
  };

  const handleRecordKeyDown = (event, item) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openDetail(item);
    }
  };

  const deleteRecord = async (event, item) => {
    event.stopPropagation();

    const ok = window.confirm(`確定要刪除「${item.title || "未命名影片"}」這筆紀錄嗎？`);
    if (!ok) return;

    setDeletingId(item.id);
    setError(null);

    try {
      const res = await fetch(`/api/history?id=${encodeURIComponent(item.id)}`, {
        method: "DELETE",
      });
      const data = await readApiResponse(res);

      if (!res.ok) {
        throw new Error(data.error || "刪除失敗");
      }

      setRecords((current) => current?.filter((record) => record.id !== item.id) ?? current);
      setDetail((current) => (current?.id === item.id ? null : current));
    } catch (err) {
      setError(err instanceof Error ? err.message : "刪除失敗");
    } finally {
      setDeletingId(null);
    }
  };

  const loading = records === null;

  return (
    <div className="min-h-screen text-white">
      <Header showAction={false} />

      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
        <h1 className="text-4xl font-bold">歷史紀錄</h1>

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
          <span className="self-center text-base text-white/70">類型</span>
          {CATEGORIES.map((c) => {
            const active = categories.includes(c.value);

            return (
              <button
                key={c.value}
                type="button"
                onClick={() => handleCategoryToggle(c.value)}
                className={`rounded-xl px-4 py-2 text-base font-medium transition ${
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
              <article
                key={item.id}
                role="button"
                tabIndex={0}
                onClick={() => openDetail(item)}
                onKeyDown={(event) => handleRecordKeyDown(event, item)}
                className="group flex cursor-pointer flex-col gap-3 rounded-xl bg-gray-900/90 p-4 text-left ring-1 ring-white/10 transition hover:bg-gray-800/90 hover:ring-indigo-300/30 focus:outline-none focus:ring-2 focus:ring-indigo-300/60 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-indigo-300/20 bg-indigo-400/10 px-2.5 py-1 text-sm font-semibold text-indigo-100">
                      {item.category}
                    </span>
                  </div>
                  <p className="truncate font-semibold transition group-hover:text-indigo-100">
                    {item.title || "（無標題）"}
                  </p>
                  <p className="mt-1 truncate text-base text-gray-400">{item.youtube_url}</p>
                  <p className="mt-1 text-sm text-gray-500">{formatWhen(item)}</p>
                </div>
                <button
                  type="button"
                  onClick={(event) => deleteRecord(event, item)}
                  disabled={deletingId === item.id}
                  className="shrink-0 rounded-lg border border-red-300/20 bg-red-500/10 px-3 py-2 text-base font-semibold text-red-100 transition hover:border-red-200/40 hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                  aria-label={`刪除 ${item.title || "未命名影片"}`}
                >
                  {deletingId === item.id ? "刪除中" : "刪除"}
                </button>
              </article>
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
            className="max-h-[90vh] w-full max-w-6xl overflow-y-auto rounded-xl bg-gray-950/95 p-6 text-left shadow-xl ring-1 ring-white/20"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-6 flex items-start justify-between gap-4 border-b border-white/10 pb-4">
              <div>
                <p className="text-md font-medium uppercase tracking-wide text-indigo-300/90">
                  與首頁相同預覽
                </p>
                <h2 className="mt-1 text-xl font-bold text-white">{detail.title || "紀錄詳情"}</h2>
                <p className="mt-1 break-all text-base text-gray-400">{detail.youtube_url}</p>
                <p className="mt-2 text-sm text-gray-500">
                  {detail.category} · {formatWhen(detail)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setDetail(null)}
                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-transparent bg-transparent text-3xl font-medium leading-none text-white/90 transition hover:bg-red-600 hover:text-white focus:outline-none focus:ring-2 focus:ring-red-300/70"
                aria-label="關閉紀錄詳情"
              >
                ×
              </button>
            </div>
            <HistoryRecordBody
              mode={detail.mode}
              category={detail.category}
              payload={detail.payload}
            />
          </div>
        </div>
      )}
    </div>
  );
}
