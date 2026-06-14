from __future__ import annotations
from .ollama_service import LocalLLMService
from opencc import OpenCC

_cc = OpenCC("s2tw")

def to_traditional_zh(value):
    if isinstance(value, str):
        return _cc.convert(value)

    if isinstance(value, list):
        return [to_traditional_zh(item) for item in value]

    if isinstance(value, dict):
        return {
            key: to_traditional_zh(item)
            for key, item in value.items()
        }

    return value

class BaseAgent:
    name: str = "base_agent"
    role: str = ""
    output_schema: str = ""
    output_json_schema: dict | None = None

    def __init__(self, llm: LocalLLMService | None = None):
        self.llm = llm or LocalLLMService()

    def build_system_prompt(self, *, output_schema: str | None = None) -> str:
        return f"""
        你現在的身份是：

        {self.role}

        請嚴格遵守以下規則：
        1. 所有輸出文字必須使用台灣繁體中文，不得使用簡體中文。
        2. 只輸出一個完整 JSON object，不要輸出 Markdown、解釋或推理過程。
        3. 不要捏造輸入資料中不存在的事實；資料不足時請在對應欄位中保守說明。
        4. 不要輸出「摘要1」、「標籤1」、「建議1」等佔位文字。
        5. JSON 必須符合以下結構：

        {output_schema or self.output_schema}
        """

    def run(
        self,
        user_prompt: str,
        *,
        temperature: float = 0.1,
        num_predict: int = 1024,
        num_ctx: int = 8192,
        json_schema: dict | None = None,
        output_schema: str | None = None,
    ) -> dict:
        data = self.llm.generate_json(
            system_prompt=self.build_system_prompt(output_schema=output_schema),
            user_prompt=user_prompt,
            temperature=temperature,
            num_predict=num_predict,
            num_ctx=num_ctx,
            json_schema=json_schema or self.output_json_schema,
        )

        return to_traditional_zh(data)
