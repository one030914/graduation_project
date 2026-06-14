from __future__ import annotations

import json
import re
import os
import time
from typing import Any
from dotenv import load_dotenv
from ollama import Client

load_dotenv(verbose=True)


MODEL_PROFILES = {
    "small": {
        "num_ctx": 8192,
        "max_num_predict": 2200,
    },
    "large": {
        "num_ctx": 12000,
        "max_num_predict": 4096,
    },
    "standard": {
        "num_ctx": 8192,
        "max_num_predict": 3072,
    },
}


def _env_positive_int(name: str) -> int | None:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


class LocalLLMService:
    def __init__(
        self,
        model_name: str = os.getenv("OLLAMA_MODEL", "gemma3:12b"),
        host: str = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"),
    ):
        self.model_name = model_name
        self.client = Client(host=host)
        self.keep_alive = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
        self.profile_name = self._resolve_profile_name()

    def _resolve_profile_name(self) -> str:
        configured = str(os.getenv("OLLAMA_PROFILE", "auto")).strip().lower()
        if configured in MODEL_PROFILES:
            return configured

        normalized_model = self.model_name.lower()
        if "llama3.2:3b" in normalized_model:
            return "small"
        if "gemma4:12b" in normalized_model:
            return "large"
        return "standard"

    def _resolve_generation_options(
        self,
        *,
        num_predict: int,
    ) -> tuple[int, int]:
        profile = MODEL_PROFILES[self.profile_name]
        resolved_num_ctx = _env_positive_int("OLLAMA_NUM_CTX") or profile["num_ctx"]
        max_num_predict = (
            _env_positive_int("OLLAMA_MAX_NUM_PREDICT")
            or profile["max_num_predict"]
        )
        resolved_num_predict = min(max(1, num_predict), max_num_predict)
        return resolved_num_ctx, resolved_num_predict

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
        resolved_num_ctx, initial_num_predict = self._resolve_generation_options(
            num_predict=num_predict,
        )

        for attempt, prompt in enumerate(prompts, start=1):
            attempt_num_predict = initial_num_predict
            if attempt > 1 and last_done_reason == "length":
                profile_max = (
                    _env_positive_int("OLLAMA_MAX_NUM_PREDICT")
                    or MODEL_PROFILES[self.profile_name]["max_num_predict"]
                )
                attempt_num_predict = min(
                    max(initial_num_predict + 512, int(initial_num_predict * 1.5)),
                    profile_max,
                )
                prompt += (
                    "\n前一次輸出因長度上限而中斷。這次請進一步縮短文字，"
                    "每個陣列只保留最重要的項目，並務必完成整個 JSON。"
                )

            started_at = time.perf_counter()
            response = self.client.generate(
                model=self.model_name,
                system=system_prompt,
                prompt=prompt,
                format=json_schema or "json",
                think=False,
                keep_alive=self.keep_alive,
                options={
                    "temperature": 0.0 if attempt > 1 else temperature,
                    "num_predict": attempt_num_predict,
                    "num_ctx": resolved_num_ctx,
                },
            )
            elapsed = time.perf_counter() - started_at

            raw = response.get("response", "")
            done_reason = str(response.get("done_reason", "") or "")
            eval_count = int(response.get("eval_count", 0) or 0)
            eval_duration = int(response.get("eval_duration", 0) or 0)
            prompt_eval_count = int(response.get("prompt_eval_count", 0) or 0)
            load_seconds = int(response.get("load_duration", 0) or 0) / 1_000_000_000
            eval_seconds = eval_duration / 1_000_000_000
            tokens_per_second = eval_count / eval_seconds if eval_seconds > 0 else 0.0
            print(
                "=== LLM METRICS "
                f"model={self.model_name} profile={self.profile_name} "
                f"ctx={resolved_num_ctx} predict={attempt_num_predict} "
                f"attempt={attempt} elapsed={elapsed:.2f}s load={load_seconds:.2f}s "
                f"prompt_tokens={prompt_eval_count} output_tokens={eval_count} "
                f"output_speed={tokens_per_second:.2f}tok/s "
                f"done_reason={done_reason or 'unknown'} ==="
            )
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
