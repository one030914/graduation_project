import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const JOB_ID_PATTERN = /^[a-zA-Z0-9_-]+$/;
const REQUEST_TIMEOUT_MS = 10_000;

function resolveUpstreamPath(method, segments) {
  if (method === "POST" && segments.length === 1 && segments[0] === "jobs") {
    return "/jobs";
  }

  if (method === "GET" && segments.length === 1 && segments[0] === "status") {
    return "/status";
  }

  if (
    method === "GET" &&
    segments.length === 2 &&
    segments[0] === "jobs" &&
    JOB_ID_PATTERN.test(segments[1])
  ) {
    return `/jobs/${encodeURIComponent(segments[1])}`;
  }

  if (
    method === "GET" &&
    segments.length === 3 &&
    segments[0] === "jobs" &&
    JOB_ID_PATTERN.test(segments[1]) &&
    segments[2] === "result"
  ) {
    return `/jobs/${encodeURIComponent(segments[1])}/result`;
  }

  return null;
}

function getUpstreamConfig() {
  const baseUrl = process.env.INFERENCE_API_BASE?.replace(/\/+$/, "");
  if (!baseUrl) {
    throw new Error("INFERENCE_API_BASE is not configured.");
  }

  const parsedBaseUrl = new URL(baseUrl);
  if (!["http:", "https:"].includes(parsedBaseUrl.protocol)) {
    throw new Error("INFERENCE_API_BASE must use HTTP or HTTPS.");
  }

  return {
    baseUrl,
    apiSecret: process.env.INFERENCE_API_SECRET,
  };
}

async function proxyRequest(request, context) {
  const { path = [] } = await context.params;
  const upstreamPath = resolveUpstreamPath(request.method, path);

  if (!upstreamPath) {
    return NextResponse.json({ error: "Inference route not found." }, { status: 404 });
  }

  let config;
  try {
    config = getUpstreamConfig();
  } catch (error) {
    console.error("Inference proxy configuration error", error);
    return NextResponse.json(
      { error: "Inference proxy is not configured.", code: "INFERENCE_CONFIG_ERROR" },
      { status: 500 },
    );
  }

  const headers = { Accept: "application/json" };
  if (request.method === "POST") {
    headers["Content-Type"] = "application/json";
  }
  if (config.apiSecret) {
    headers.Authorization = `Bearer ${config.apiSecret}`;
  }

  try {
    const upstreamResponse = await fetch(`${config.baseUrl}${upstreamPath}`, {
      method: request.method,
      headers,
      body: request.method === "POST" ? await request.text() : undefined,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });

    if (upstreamResponse.status === 401 || upstreamResponse.status === 403) {
      return NextResponse.json(
        { error: "Inference service authentication failed.", code: "INFERENCE_AUTH_FAILED" },
        { status: 502 },
      );
    }

    const body = await upstreamResponse.text();
    return new Response(body, {
      status: upstreamResponse.status,
      headers: {
        "Content-Type": upstreamResponse.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    console.error("Inference service is unavailable", error);
    return NextResponse.json(
      { error: "推理服務目前未啟動，請稍後再試。", code: "INFERENCE_OFFLINE" },
      { status: 503 },
    );
  }
}

export async function GET(request, context) {
  return proxyRequest(request, context);
}

export async function POST(request, context) {
  return proxyRequest(request, context);
}
