from __future__ import annotations
import json
from agents.base import BaseAgent

class IntentAgent(BaseAgent):
    name = "intent_agent"

    role = """
    你是一位 YouTube 社群留言行動訊號分析師。
    你的任務是從留言中找出創作者需要處理的高價值行動訊號。
    你必須根據完整語意分類，而不是只看單一關鍵字。
    """

    output_schema = """
    {
    "items": [
        {
        "id": "留言ID",
        "intent": "question | correction | advice | wishlist | resource | ignore",
        "reason": "簡短判斷理由",
        "priority": "high | medium | low"
        }
    ]
    }
    """

    def classify_batch(self, comments: list[dict]) -> dict:
        user_prompt = f"""
        請根據完整語意分類以下 YouTube 留言。

        只允許使用以下 6 種分類：

        1. question
        真正需要創作者或其他觀眾回答的問題。
        注意：不要只因為出現「怎麼、如何、嗎」就判定為 question。

        2. correction
        指出影片內容、字幕、數字、資訊、事實或說法錯誤。

        3. advice
        給創作者的建議、提醒、勸告、處理方式建議、法律或措辭提醒。
        例如「不要再這樣說」、「建議補充說明」、「之後發言要小心」。

        4. wishlist
        希望創作者未來補充、拍攝、延伸或更新的內容。
        例如「希望下一集講...」、「可以再拍...」。

        5. resource
        提供外部連結、資料來源、證據、官方資料，或明確指出參考資料。

        6. ignore
        支持、稱讚、感謝、聲援、玩梗、純情緒表達、閒聊、無需創作者處理的留言。

        重要規則：
        - 最終分類必須根據整句語意，不是單一關鍵字。
        - 如果留言是在支持、感謝、聲援或抖內，請分類為 ignore。
        - 如果留言是在提醒創作者如何處理事情，請分類為 advice。
        - 如果留言只是情緒表達，不要硬分類成 question。
        - 每則留言都必須回傳一個分類。
        - 回傳 items 的 id 必須對應輸入留言的 id。
        - 只輸出 JSON object，不要 Markdown。

        留言資料：
        {json.dumps(comments, ensure_ascii=False, indent=2)}
        """
        return self.run(
            user_prompt,
            temperature=0.1,
            num_predict=1600,
            num_ctx=12000,
        )