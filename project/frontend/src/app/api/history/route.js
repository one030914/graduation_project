import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MODE_TO_CATEGORY = {
  analyze: "綜合分析",
  summary: "留言摘要",
  keyword: "熱門關鍵詞",
  topics: "熱門主題",
  emotion: "情緒風向",
  criticism: "批評回饋",
  timeline: "時間軸熱點",
  video_content: "影片內容脈絡",
};

const FILTER_TO_MODE = {
  綜合分析: ["analyze"],
  分析: ["analyze"],
  留言摘要: ["summary"],
  摘要: ["summary"],
  熱門關鍵詞: ["keyword"],
  關鍵詞: ["keyword"],
  熱門主題: ["topics"],
  主題: ["topics"],
  主題分析: ["topics"],
  情緒風向: ["emotion"],
  情緒: ["emotion"],
  情緒分析: ["emotion"],
  批評回饋: ["criticism"],
  批評: ["criticism"],
  批評分析: ["criticism"],
  時間軸熱點: ["timeline"],
  時間軸: ["timeline"],
  時間軸分析: ["timeline"],
  影片內容脈絡: ["video_content"],
  影片內容: ["video_content"],
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
  try {
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
          categories.flatMap((category) => FILTER_TO_MODE[category] ?? [category]),
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
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to load history.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(request) {
  const { searchParams } = new URL(request.url);
  const id = Number(searchParams.get("id"));

  if (!Number.isInteger(id) || id <= 0) {
    return NextResponse.json({ error: "A valid id is required." }, { status: 400 });
  }

  try {
    const result = await prisma.analysis.deleteMany({
      where: { id },
    });

    if (result.count === 0) {
      return NextResponse.json({ error: "Record not found." }, { status: 404 });
    }

    return NextResponse.json({ deleted: true, id });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to delete record.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
