"use client";

import { useRef, useState } from "react";
import { API_BASE } from "@/lib/apiBase";
import {
  AnalysisResultView,
  SummaryResultView,
  KeywordResultView,
  TopicsResultView,
  EmotionRecordView,
  CriticismResultView,
  TimelineResultView,
  VideoContentResultView,
} from "@/lib/ResultViews";
import { Input } from "@/components/Input";
import { Header } from "@/components/Header";
import { JobStatusPanel } from "@/components/JobStatusPanel";

const MODE = {
  analyze: "analyze",
  summary: "summary",
  keyword: "keyword",
  topics: "topics",
  emotion: "emotion",
  criticism: "criticism",
  timeline: "timeline",
  videoContent: "videoContent",
};

const JOB_MODE = {
  analyze: "analyze",
  summary: "summary",
  keyword: "keyword",
  topics: "topics",
  emotion: "emotion",
  criticism: "criticism",
  timeline: "timeline",
  videoContent: "video_content",
};

const POLL_INTERVAL_MS = 1200;
const ANALYZE_POLL_INTERVAL_MS = 600;

const ANALYZE_PLACEHOLDER = {
  is_partial: true,
  status: "partial",
  title: "分析準備中…",
  total_comments: 0,
  dashboard_data: {},
  data_sources: {},
  completed_stages: [],
};

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export default function Page() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [visiblePanel, setVisiblePanel] = useState(null);
  const [results, setResults] = useState({});
  const [jobState, setJobState] = useState(null);
  const activeJobRef = useRef(null);

  const updateResult = (action, result) => {
    setResults((prev) => ({
      ...prev,
      [action]: result,
    }));
  };

  const resetOtherPanel = (action) => {
    setResults({});
    setVisiblePanel(action);
  };

  const fetchJobResult = async (jobId) => {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/result`);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Failed to fetch job result.");
    }

    return data;
  };

  const saveAnalysisRecord = async ({ jobId, mode, url, payload }) => {
    try {
      const res = await fetch("/api/analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: jobId,
          mode,
          url,
          payload,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Failed to save analysis.");
      }
    } catch (error) {
      console.error("Failed to save analysis record", error);
    }
  };

  const pollJobUntilDone = async (jobId, action) => {
    const pollMs = action === MODE.analyze ? ANALYZE_POLL_INTERVAL_MS : POLL_INTERVAL_MS;

    while (activeJobRef.current === jobId) {
      const statusRes = await fetch(`${API_BASE}/jobs/${jobId}`);
      const statusData = await statusRes.json();

      if (!statusRes.ok) {
        throw new Error(statusData.error || "Failed to fetch job status.");
      }

      setJobState((prev) => ({
        jobId,
        action,
        status: statusData.status,
        mode: statusData.mode,
        fromCache: statusData.from_cache,
        error: statusData.error || null,
        stage: statusData.stage || prev?.stage || "",
        stageProgress: statusData.stage_progress ?? prev?.stageProgress ?? 0,
      }));

      if (
        action === MODE.analyze &&
        statusData.partial_result &&
        typeof statusData.partial_result === "object"
      ) {
        updateResult(action, statusData.partial_result);
      }

      if (statusData.status === "completed") {
        const resultData = await fetchJobResult(jobId);
        const result = resultData.result ?? null;
        updateResult(action, result);
        void saveAnalysisRecord({
          jobId,
          mode: resultData.mode || statusData.mode || JOB_MODE[action],
          url: text.trim(),
          payload: result,
        });
        setJobState((prev) =>
          prev && prev.jobId === jobId
            ? {
                ...prev,
                status: "completed",
                fromCache: statusData.from_cache,
                stage: "synthesize",
                stageProgress: 1,
              }
            : prev,
        );
        return;
      }

      if (statusData.status === "failed") {
        throw new Error(statusData.error || "Job failed.");
      }

      if (statusData.status === "cancelled") {
        activeJobRef.current = null;
        setJobState((prev) =>
          prev && prev.jobId === jobId
            ? { ...prev, status: "cancelled", error: statusData.error || null }
            : prev,
        );
        return;
      }

      await sleep(pollMs);
    }
  };

  const handleCancelJob = async () => {
    const jobId = activeJobRef.current || jobState?.jobId;
    if (!jobId) return;

    activeJobRef.current = null;
    setLoading(false);
    setJobState((prev) =>
      prev && prev.jobId === jobId ? { ...prev, status: "cancelled", error: "已停止分析。" } : prev,
    );

    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Failed to cancel job.");
      }
      setJobState((prev) =>
        prev && prev.jobId === jobId
          ? { ...prev, status: data.status || "cancelled", error: "已停止分析。" }
          : prev,
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to cancel job.";
      setJobState((prev) =>
        prev && prev.jobId === jobId ? { ...prev, status: "failed", error: message } : prev,
      );
    }
  };

  const handleSubmit = async (action) => {
    if (!text || loading) return;

    const trimmedText = text.trim();
    if (!trimmedText) return;

    resetOtherPanel(action);
    if (action === MODE.analyze) {
      updateResult(MODE.analyze, ANALYZE_PLACEHOLDER);
    }
    setLoading(true);
    setJobState({
      jobId: null,
      action,
      status: "submitting",
      mode: JOB_MODE[action],
      fromCache: false,
      error: null,
    });

    try {
      const createRes = await fetch(`${API_BASE}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_url: trimmedText,
          job_mode: JOB_MODE[action],
        }),
      });
      const createData = await createRes.json();

      if (!createRes.ok) {
        throw new Error(createData.error || "Failed to create job.");
      }

      const jobId = createData.job_id;
      activeJobRef.current = jobId;
      setJobState({
        jobId,
        action,
        status: createData.status || "queued",
        mode: createData.mode || JOB_MODE[action],
        fromCache: false,
        error: null,
      });

      await pollJobUntilDone(jobId, action);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Job failed.";
      setJobState((prev) => ({
        ...(prev ?? {}),
        action,
        status: "failed",
        error: message,
      }));
    } finally {
      activeJobRef.current = null;
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen text-white">
      <Header />

      <div className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6">
        <main className="space-y-6">
          <Input text={text} loading={loading} activeAction={visiblePanel} onTextChange={setText} onSubmit={handleSubmit} />

          {jobState && <JobStatusPanel jobState={jobState} onCancel={handleCancelJob} />}

          {visiblePanel === MODE.analyze && results[MODE.analyze] && (
            <AnalysisResultView
              key={`${jobState?.stage || "init"}-${jobState?.stageProgress ?? 0}-${results[MODE.analyze]?.completed_stages?.length ?? 0}`}
              result={results[MODE.analyze]}
            />
          )}

          {visiblePanel === MODE.summary && results[MODE.summary] && (
            <SummaryResultView result={results[MODE.summary]} />
          )}

          {visiblePanel === MODE.keyword && results[MODE.keyword] && (
            <KeywordResultView result={results[MODE.keyword]} />
          )}

          {visiblePanel === MODE.topics && results[MODE.topics] && (
            <TopicsResultView result={results[MODE.topics]} />
          )}

          {visiblePanel === MODE.emotion && results[MODE.emotion] && (
            <EmotionRecordView result={results[MODE.emotion]} />
          )}

          {visiblePanel === MODE.criticism && results[MODE.criticism] && (
            <CriticismResultView result={results[MODE.criticism]} />
          )}

          {visiblePanel === MODE.timeline && results[MODE.timeline] && (
            <TimelineResultView result={results[MODE.timeline]} />
          )}

          {visiblePanel === MODE.videoContent && results[MODE.videoContent] && (
            <VideoContentResultView result={results[MODE.videoContent]} />
          )}
        </main>
      </div>
    </div>
  );
}
