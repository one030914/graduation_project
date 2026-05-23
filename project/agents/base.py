from __future__ import annotations
from .ollama_service import LocalLLMService

class BaseAgent:
    name: str = "base_agent"
    role: str = ""
    output_schema: str = ""

    def __init__(self, llm: LocalLLMService | None = None):
        self.llm = llm or LocalLLMService()

    def build_system_prompt(self) -> str:
        return f"""
        你現在的身份是：

        {self.role}

        請嚴格遵守以下規則：
        1. 使用繁體中文。
        2. 只能輸出 JSON object。
        3. 輸出的第一個字元必須是 {{，最後一個字元必須是 }}。
        4. 不要輸出 Markdown。
        5. 不要輸出 ```json。
        6. 不要輸出任何解釋文字。
        7. 不要捏造輸入資料中不存在的事實。
        8. 如果資料不足，請在 JSON 欄位中說明資料不足。
        9. 不要輸出「摘要1」、「標籤1」、「建議1」這種佔位文字。
        10. JSON 格式必須符合以下結構：

        {self.output_schema}
        """

    def run(
        self,
        user_prompt: str,
        *,
        temperature: float = 0.1,
        num_predict: int = 1024,
        num_ctx: int = 8192,
    ) -> dict:
        return self.llm.generate_json(
            system_prompt=self.build_system_prompt(),
            user_prompt=user_prompt,
            temperature=temperature,
            num_predict=num_predict,
            num_ctx=num_ctx,
        )