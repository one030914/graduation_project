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

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function hasFailedPayload(payload) {
  if (!payload || typeof payload !== "object") return true;
  if (payload.error) return true;

  const status = typeof payload.status === "string" ? payload.status.toLowerCase() : "";
  return status === "error" || status === "failed";
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

  const createJob = async (url, action) => {
    const createRes = await fetch(`${API_BASE}/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        video_url: url,
        job_mode: JOB_MODE[action],
      }),
    });
    const createData = await createRes.json();

    if (!createRes.ok) {
      throw new Error(createData.error || "Failed to create job.");
    }

    return createData;
  };

  const fetchJobResult = async (jobId) => {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/result`);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Failed to fetch job result.");
    }

    return data;
  };

  const saveAnalysisRecord = async ({ jobId, mode, url, payload, fromCache = false }) => {
    if (fromCache || hasFailedPayload(payload)) return;

    try {
      const res = await fetch("/api/analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: jobId,
          mode,
          url,
          payload,
          from_cache: fromCache,
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

  const pollJobUntilDone = async (jobId, action, url) => {
    while (activeJobRef.current === jobId) {
      const statusRes = await fetch(`${API_BASE}/jobs/${jobId}`);
      const statusData = await statusRes.json();

      if (!statusRes.ok) {
        throw new Error(statusData.error || "Failed to fetch job status.");
      }

      setJobState({
        jobId,
        action,
        status: statusData.status,
        mode: statusData.mode,
        fromCache: statusData.from_cache,
        error: statusData.error || null,
      });

      if (statusData.status === "completed") {
        const resultData = await fetchJobResult(jobId);
        const result = resultData.result ?? null;
        updateResult(action, result);
        void saveAnalysisRecord({
          jobId,
          mode: resultData.mode || statusData.mode || JOB_MODE[action],
          url,
          payload: result,
          fromCache: Boolean(statusData.from_cache),
        });
        setJobState((prev) =>
          prev && prev.jobId === jobId
            ? { ...prev, status: "completed", fromCache: statusData.from_cache }
            : prev,
        );
        return;
      }

      if (statusData.status === "failed") {
        throw new Error(statusData.error || "Job failed.");
      }

      await sleep(POLL_INTERVAL_MS);
    }
  };

  const handleProgressiveAnalyze = async (url) => {
    const createData = await createJob(url, MODE.analyze);
    const jobId = createData.job_id;
    activeJobRef.current = jobId;
    setJobState({
      jobId,
      action: MODE.analyze,
      status: createData.status || "queued",
      mode: createData.mode || JOB_MODE.analyze,
      fromCache: false,
      error: null,
    });

    while (activeJobRef.current === jobId) {
      const statusRes = await fetch(`${API_BASE}/jobs/${jobId}`);
      const statusData = await statusRes.json();

      if (!statusRes.ok) {
        throw new Error(statusData.error || "Failed to fetch analyze status.");
      }

      if (statusData.partial_result) {
        updateResult(MODE.analyze, statusData.partial_result);
      }

      setJobState({
        jobId,
        action: MODE.analyze,
        status: statusData.status,
        mode: statusData.mode,
        fromCache: statusData.from_cache,
        error: statusData.error || null,
      });

      if (statusData.status === "completed") {
        const resultData = await fetchJobResult(jobId);
        const result = resultData.result ?? null;
        updateResult(MODE.analyze, result);
        void saveAnalysisRecord({
          jobId,
          mode: resultData.mode || statusData.mode || JOB_MODE.analyze,
          url,
          payload: result,
          fromCache: Boolean(statusData.from_cache),
        });
        setJobState((prev) =>
          prev && prev.jobId === jobId
            ? { ...prev, status: "completed", fromCache: statusData.from_cache }
            : prev,
        );
        return;
      }

      if (statusData.status === "failed") {
        throw new Error(statusData.error || "Analyze job failed.");
      }

      await sleep(POLL_INTERVAL_MS);
    }
  };

  const handleSubmit = async (action) => {
    if (!text || loading) return;

    const trimmedText = text.trim();
    if (!trimmedText) return;

    resetOtherPanel(action);
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
      if (action === MODE.analyze) {
        await handleProgressiveAnalyze(trimmedText);
        return;
      }

      const createData = await createJob(trimmedText, action);
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

      await pollJobUntilDone(jobId, action, trimmedText);
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

          {jobState && <JobStatusPanel jobState={jobState} />}

          {visiblePanel === MODE.analyze && results[MODE.analyze] && (
            <AnalysisResultView result={results[MODE.analyze]} />
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
