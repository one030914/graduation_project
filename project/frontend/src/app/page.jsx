"use client";

import { useRef, useState } from "react";
import { API_BASE } from "@/lib/apiBase";
import { AnalysisResultView, TopicsResultView, VideoContentResultView } from "@/lib/ResultViews";
import { Input } from "@/components/Input";
import { Header } from "@/components/Header";
import { JobStatusPanel } from "@/components/JobStatusPanel";

const MODE = {
  analyze: "analyze",
  topics: "topics",
  videoContent: "videoContent",
};

const JOB_MODE = {
  analyze: "analyze",
  topics: "topics",
  videoContent: "video_content",
};

const POLL_INTERVAL_MS = 1200;

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export default function Page() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [visiblePanel, setVisiblePanel] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [topicsResult, setTopicsResult] = useState(null);
  const [videoContentResult, setVideoContentResult] = useState(null);
  const [jobState, setJobState] = useState(null);
  const activeJobRef = useRef(null);

  const updateResult = (action, result) => {
    if (action === MODE.analyze) {
      setAnalysisResult(result);
      return;
    }

    if (action === MODE.topics) {
      setTopicsResult(result);
      return;
    }

    if (action === MODE.videoContent) {
      setVideoContentResult(result);
    }
  };

  const resetOtherPanel = (action) => {
    setAnalysisResult(null);
    setTopicsResult(null);
    setVideoContentResult(null);
    setVisiblePanel(action);
  };

  const fetchJobResult = async (jobId) => {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/result`);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Failed to fetch job result.");
    }

    return data.result ?? null;
  };

  const pollJobUntilDone = async (jobId, action) => {
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
        const result = await fetchJobResult(jobId);
        updateResult(action, result);
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

      if (statusData.status === "cancelled") {
        activeJobRef.current = null;
        setJobState((prev) =>
          prev && prev.jobId === jobId
            ? { ...prev, status: "cancelled", error: statusData.error || null }
            : prev,
        );
        return;
      }

      await sleep(POLL_INTERVAL_MS);
    }
  };

  const handleCancelJob = async () => {
    const jobId = activeJobRef.current || jobState?.jobId;
    if (!jobId) return;

    activeJobRef.current = null;
    setLoading(false);
    setJobState((prev) =>
      prev && prev.jobId === jobId
        ? { ...prev, status: "cancelled", error: "已停止分析。" }
        : prev,
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
        prev && prev.jobId === jobId
          ? { ...prev, status: "failed", error: message }
          : prev,
      );
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

      <div className="mx-auto max-w-5xl space-y-8 px-4 py-8 sm:px-6">
        <main className="space-y-6">
          <Input
            text={text}
            loading={loading}
            onTextChange={setText}
            onSubmit={handleSubmit}
          />

          {jobState && <JobStatusPanel jobState={jobState} onCancel={handleCancelJob} />}

          {visiblePanel === MODE.analyze && analysisResult && (
            <AnalysisResultView result={analysisResult} />
          )}

          {visiblePanel === MODE.topics && topicsResult && (
            <TopicsResultView result={topicsResult} />
          )}

          {visiblePanel === MODE.videoContent && videoContentResult && (
            <VideoContentResultView result={videoContentResult} />
          )}
        </main>
      </div>
    </div>
  );
}
