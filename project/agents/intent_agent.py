from __future__ import annotations
import json
from agents.base import BaseAgent

class IntentAgent(BaseAgent):
    name = "intent_agent"

    role = """
    你是一位 YouTube 社群留言營運分析師。
    你擅長從提問、勘誤、許願、抱怨與外部資源留言中，
    挑出創作者最需要優先處理的高價值留言。
    """

    output_schema = """
    {
    "summary": ["意圖分析摘要 1", "意圖分析摘要 2"],
    "priority_questions": ["優先回覆問題 1", "優先回覆問題 2"],
    "priority_corrections": ["重要勘誤 1", "重要勘誤 2"],
    "content_ideas": ["可發展成下一集的題材 1", "題材 2"],
    "action_suggestions": ["行動建議 1", "行動建議 2"]
    }
    """

    def analyze(self, payload: dict) -> dict:
        user_prompt = f"""
        以下是系統根據規則分類出的 YouTube 留言意圖結果。
        請你從中整理出最值得創作者處理的行動重點。

        要求：
        - 不要重新分類全部留言。
        - 請優先考慮按讚數、回覆數與內容具體程度。
        - 不要捏造留言中沒有出現的資訊。
        - 輸出必須是 JSON。

        資料：
        {json.dumps(payload, ensure_ascii=False, indent=2)}
        """
        return self.run(user_prompt, temperature=0.2)