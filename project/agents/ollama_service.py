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
    ) -> dict[str, Any]:
        response = self.client.generate(
            model=self.model_name,
            system=system_prompt,
            prompt=user_prompt,
            format="json",
            options={
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
            },
        )

        raw = response.get("response", "")
        print("=== LLM RAW RESPONSE START ===")
        print(repr(raw[:1000]))
        print("=== LLM RAW RESPONSE END ===")

        try:
            json_text = self._extract_json_text(raw)
            data = json.loads(json_text)
        except Exception as exc:
            raise ValueError(
                f"Failed to parse LLM JSON: {type(exc).__name__}: {exc}. "
                f"Raw preview={repr(raw[:500])}"
            )

        if not isinstance(data, dict):
            raise ValueError(f"LLM result must be JSON object, got {type(data).__name__}")

        return data