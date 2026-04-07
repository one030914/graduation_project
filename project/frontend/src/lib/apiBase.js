const fallbackBase = "http://127.0.0.1:8000";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || fallbackBase;
