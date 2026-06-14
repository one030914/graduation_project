from __future__ import annotations

import json
import re
import os
from typing import Any
from dotenv import load_dotenv
from ollama import Client

load_dotenv(verbose=True)

class LocalLLMService:
    def __init__(
        self,
        model_name: str = os.getenv("OLLAMA_MODEL", "gemma3:12b"),
        host: str = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"),
    ):
        self.model_name = model_name
        self.client = Client(host=host)

    def _extract_json_text(self, raw: str) -> str:
        raw = (raw or "").strip()

        if not raw:
            raise ValueError("LLM returned empty response.")

        if raw.startswith("```"):
            raw = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                raw,
                flags=re.IGNORECASE | re.DOTALL,
            ).strip()

        start = raw.find("{")
        end = raw.rfind("}")

        if start != -1 and end != -1 and end > start:
            raw = raw[start : end + 1].strip()

        return raw

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        num_predict: int = 1024,
        num_ctx: int = 8192,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        prompts = [user_prompt]
        if json_schema is not None:
            prompts.append(
                f"{user_prompt}\n\n"
                "前一次輸出不是完整有效的 JSON。請重新輸出一次，內容保持精簡，"
                "嚴格符合指定 JSON Schema，不可新增欄位，並確認所有括號、引號與陣列都完整閉合。"
            )

        last_error: Exception | None = None
        last_raw = ""
        last_done_reason = ""

        for attempt, prompt in enumerate(prompts, start=1):
            response = self.client.generate(
                model=self.model_name,
                system=system_prompt,
                prompt=prompt,
                format=json_schema or "json",
                think=False,
                options={
                    "temperature": 0.0 if attempt > 1 else temperature,
                    "num_predict": num_predict,
                    "num_ctx": num_ctx,
                },
            )

            raw = response.get("response", "")
            done_reason = str(response.get("done_reason", "") or "")
            print(f"=== LLM RAW RESPONSE ATTEMPT {attempt} START ===")
            print(repr(raw[:1000]))
            print(f"=== LLM RAW RESPONSE ATTEMPT {attempt} END ===")

            try:
                json_text = self._extract_json_text(raw)
                data = json.loads(json_text)
                if not isinstance(data, dict):
                    raise ValueError(
                        f"LLM result must be JSON object, got {type(data).__name__}"
                    )
                return data
            except Exception as exc:
                last_error = exc
                last_raw = raw
                last_done_reason = done_reason

        hint = ""
        if re.search(r'^[\s`]*\{?\s*"?thought', last_raw, flags=re.IGNORECASE):
            hint = " Hint: model emitted a thought/reasoning field instead of the requested JSON schema."
        if last_done_reason:
            hint += f" Ollama done_reason={last_done_reason}."
        raise ValueError(
            f"Failed to parse LLM JSON after {len(prompts)} attempt(s): "
            f"{type(last_error).__name__}: {last_error}.{hint} "
            f"Raw preview={repr(last_raw[:500])}"
        )
