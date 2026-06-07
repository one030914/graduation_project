from __future__ import annotations

import json

from agents.base import BaseAgent

class AnalyzeAgent(BaseAgent):
    name = "analyze_agent"

    role = """
    你是一位 YouTube 創作者數據顧問。
    你擅長整合留言摘要、情緒風向、熱門主題、行動訊號、批評改善點、關鍵詞與時間軸熱點，
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

    output_json_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "quick_summary",
            "tags",
            "creator_actions",
            "viewer_tips",
        ],
        "properties": {
            "quick_summary": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {"type": "string"},
            },
            "tags": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {"type": "string"},
            },
            "creator_actions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {"type": "string"},
            },
            "viewer_tips": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {"type": "string"},
            },
        },
    }

    def analyze(self, payload: dict) -> dict:
        user_prompt = f"""
        以下是系統已完成的 YouTube 留言結構化分析結果。
        請根據各分類資料產生主分析洞察。

        資料分類說明：
        - summary_context：留言區整體摘要，適合用於智慧快報。
        - emotion_context：整體情緒、輿情溫度、主導情緒。
        - topic_context：熱門討論主題，適合用於 top_topics 與摘要。
        - intent_context：創作者可行動訊號，例如問題、勘誤、建議、許願、外部資源。
        - criticism_context：批評、不滿原因、改善方向，適合轉成創作者行動建議。
        - keyword_context：熱門標籤與關鍵詞，適合產生 tags。
        - timeline_context：留言提及的影片時間點熱點，適合產生觀看提示。
        - data_quality：資料不足或失敗提醒，不得忽略。
        - video_content：影片內容脈絡，提供影片摘要、章節與創作者建議，用來避免只靠留言誤判影片主題。

        要求：
        1. 不要重新分類留言。
        2. 不要捏造資料中不存在的內容。
        3. 如果某資料來源 status 是 insufficient_data，請保守描述，不要硬下結論。
        4. 如果 criticism_context 資料不足，不要說風向良好。
        5. 如果 timeline_context.status 是 insufficient_data，請在必要時說明時間軸資料不足。
        6. creator_actions 必須具體、可執行。
        7. tags 必須短，適合放在 Discord Embed。
        8. quick_summary 最多 3 條。
        9. creator_actions 最多 3 條。
        10. viewer_tips 最多 3 條。
        11. 所有輸出文字請使用台灣繁體中文。

        分析資料：
        {json.dumps(payload, ensure_ascii=False, indent=2)}
        """
        return self.run(
            user_prompt,
            temperature=0.2,
            num_predict=1400,
            num_ctx=12000,
        )