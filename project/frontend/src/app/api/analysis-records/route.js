import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export const runtime = "nodejs";

function getTitle(payload, fallback) {
  if (payload && typeof payload === "object") {
    const title = typeof payload.title === "string" ? payload.title.trim() : "";
    if (title) return title;

    const videoId = typeof payload.video_id === "string" ? payload.video_id.trim() : "";
    if (videoId) return videoId;
  }

  return fallback;
}

function hasFailedPayload(payload) {
  if (!payload || typeof payload !== "object") return true;
  if (payload.error) return true;

  const status = typeof payload.status === "string" ? payload.status.toLowerCase() : "";
  return status === "error" || status === "failed";
}

export async function POST(request) {
  try {
    const body = await request.json();
    const jobId = typeof body.job_id === "string" ? body.job_id.trim() : "";
    const mode = typeof body.mode === "string" ? body.mode.trim() : "";
    const url = typeof body.url === "string" ? body.url.trim() : "";
    const payload = body.payload;
    const fromCache = Boolean(body.from_cache || body.fromCache);

    if (!jobId || !mode || !url || payload == null) {
      return NextResponse.json(
        { error: "job_id, mode, url, and payload are required." },
        { status: 400 },
      );
    }

    if (fromCache) {
      return NextResponse.json({ saved: false, from_cache: true });
    }

    if (hasFailedPayload(payload)) {
      return NextResponse.json({ saved: false, failed_payload: true });
    }

    const existing = await prisma.analysis.findFirst({
      where: { job_id: jobId },
      select: { id: true },
    });

    if (existing) {
      return NextResponse.json({ id: existing.id, saved: false, duplicate: true });
    }

    const record = await prisma.analysis.create({
      data: {
        job_id: jobId,
        mode,
        title: getTitle(payload, "未命名影片"),
        url,
        payload,
      },
      select: { id: true },
    });

    return NextResponse.json({ id: record.id, saved: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to save analysis record.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
