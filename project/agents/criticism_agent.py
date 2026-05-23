from __future__ import annotations
import json
from agents.base import BaseAgent

class CriticismAgent(BaseAgent):
    name = "criticism_agent"

    role = """
    你是一位 YouTube 社群輿情觀測分析師。
    你擅長從留言中整理觀眾的批評、抱怨、質疑、反對意見與具體改進建議。
    你的任務不是放大負面情緒，而是客觀找出可供創作者改進或澄清的訊號。
    """

    output_schema = """
    {
    "main_criticisms": ["具體批評點"],
    "discontent_reasons": ["觀眾不滿或質疑的底層原因"],
    "suggestions": ["觀眾提出或可推導出的具體改進建議"]
    }
    """

    def analyze(
        self,
        *,
        title: str,
        comments: list[str],
        max_comments: int = 180,
    ) -> dict:
        sampled_comments = [
            str(c).strip()
            for c in comments
            if str(c).strip()
        ][:max_comments]

        comments_block = "\n".join(
            f"{i + 1}. {comment}"
            for i, comment in enumerate(sampled_comments)
        )

        payload = {
            "video_title": title,
            "comments": sampled_comments,
        }

        user_prompt = f"""
        以下是 YouTube 影片留言資料，請分析其中的批評、抱怨、質疑與改進建議。

        重要規則：
        1. 不要把少數負面留言誇大成整體負評。
        2. 如果留言大多正面，也要只挑出具建設性的批評或疑問。
        3. 如果是情緒性謾罵，請提煉成具體問題，不要直接複製攻擊字句。
        4. 不要捏造留言中沒有出現的批評。
        5. 每一點都要具體，不要寫「觀眾不滿」這種空泛句。
        6. 輸出必須是 JSON object。
        7. 每個陣列最多 5 項。

        影片標題：
        {title}

        留言清單：
        {comments_block}

        原始結構化資料：
        {json.dumps(payload, ensure_ascii=False)}
        """

        return self.run(
            user_prompt,
            temperature=0.1,
            num_predict=1024,
            num_ctx=8192,
        )