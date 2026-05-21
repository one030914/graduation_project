import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
export const runtime = "nodejs";

const MODE_TO_CATEGORY = {
  analyze: "分析",
  summary: "摘要",
  keyword: "關鍵詞",
  topics: "主題",
  emotion: "情緒",
};

const CATEGORY_TO_MODE = {
  分析: ["analyze"],
  摘要: ["summary"],
  關鍵詞: ["keyword"],
  主題: ["topics"],
  主題分析: ["topics"],
  情緒: ["emotion"],
  情緒分析: ["emotion"],
};

function toHistoryRecord(record) {
  return {
    id: record.id,
    job_id: record.job_id,
    mode: record.mode,
    category: MODE_TO_CATEGORY[record.mode] ?? record.mode ?? "未分類",
    title: record.title,
    youtube_url: record.url,
    payload: record.payload,
    analysis_date: record.createdAt,
  };
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const categories = searchParams
    .getAll("category")
    .map((value) => value.trim())
    .filter(Boolean);
  const q = searchParams.get("q")?.trim() ?? "";

  const where = {};

  if (categories.length > 0) {
    const modes = [
      ...new Set(
        categories.flatMap((category) => CATEGORY_TO_MODE[category] ?? [category]),
      ),
    ];

    where.mode = { in: modes };
  }

  if (q) {
    where.OR = [
      { title: { contains: q, mode: "insensitive" } },
      { url: { contains: q, mode: "insensitive" } },
    ];
  }

  const records = await prisma.analysis.findMany({
    where,
    orderBy: { createdAt: "desc" },
    take: 100,
  });

  return NextResponse.json({
    records: records.map(toHistoryRecord),
  });
}
