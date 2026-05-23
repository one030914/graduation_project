from __future__ import annotations

import json

from agents.base import BaseAgent


class AnalyzeAgent(BaseAgent):
    name = "analyze_agent"

    role = """
    你是一位 YouTube 創作者數據顧問。
    你擅長整合留言情緒、熱門主題、觀眾意圖與影片時間軸熱點，
    並將分析結果轉換成清楚、可執行的洞察建議。
    """

    output_schema = """
    {
    "quick_summary": ["智慧快報 1", "智慧快報 2", "智慧快報 3"],
    "tags": ["標籤1", "標籤2", "標籤3"],
    "creator_actions": ["創作者行動建議 1", "創作者行動建議 2"],
    "viewer_tips": ["觀眾觀看提示 1", "觀眾觀看提示 2"]
    }
    """

    def analyze(self, payload: dict) -> dict:
        user_prompt = f"""
        以下是系統已完成的 YouTube 留言結構化分析結果。
        請根據資料產生綜合洞察。

        要求：
        - 不要重新分類留言。
        - 不要推測資料中不存在的內容。
        - 如果 timeline.status 是 insufficient_data，請在摘要中說明時間軸資料不足。
        - creator_actions 要具體、可執行。
        - tags 要短，適合放在 Discord Embed。
        - quick_summary 最多 3 條。
        - creator_actions 最多 3 條。
        - viewer_tips 最多 3 條。

        分析資料：
        {json.dumps(payload, ensure_ascii=False, indent=2)}
        """
        return self.run(user_prompt, temperature=0.2)