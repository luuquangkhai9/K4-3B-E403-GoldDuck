"""Optional OpenAI adapter; extractive mode needs no SDK or API key."""

import os
import json
from typing import Any

from .prompts import SYSTEM_PROMPT
from app.runtime import configure_windows_runtime, remaining_timeout


class AnswerGenerator:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: Any = None,
        timeout: float = 30.0,
        temperature: float | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL") or "gpt-5.6"
        self.client = client
        self.timeout = timeout
        # Every call here is extraction/classification under strict grounding
        # rules, so temperature=0 would help determinism if the model allowed
        # it — but reasoning-tier models (this default gpt-5.6 included)
        # reject the parameter outright ("Unsupported parameter: temperature
        # is not supported with this model"), turning every call into a 400
        # and silently degrading to the non-AI fallback. Leave unset (model's
        # own default) unless the configured model is verified to accept it.
        self.temperature = temperature

    @property
    def available(self) -> bool:
        return self.client is not None or bool(self.api_key.strip())

    def generate(self, prompt: str, *, instructions: str | None = None) -> str:
        return self._generate(prompt, instructions=instructions)

    def generate_json(self, prompt: str, *, instructions: str, schema: dict, name: str,
                      timeout: float = 20.0) -> dict:
        """Strict output for bounded planning/review; callers validate semantics."""
        text = self._generate(prompt, instructions=instructions, timeout=timeout, text={
            "format": {"type": "json_schema", "name": name, "schema": schema, "strict": True},
        }, max_output_tokens=4000)
        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError("Expected a JSON object")
        return result

    def _generate(self, prompt: str, *, instructions: str | None = None,
                  timeout: float | None = None, max_output_tokens: int = 2000, **options) -> str:
        if not self.available:
            return ""
        configure_windows_runtime()
        if self.client is None:
            from openai import OpenAI

            self.client = OpenAI(
                api_key=self.api_key, timeout=self.timeout, max_retries=0
            )
        kwargs: dict[str, Any] = {}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions if instructions is not None else SYSTEM_PROMPT,
            input=prompt,
            max_output_tokens=max_output_tokens,
            store=False,
            timeout=remaining_timeout(min(self.timeout, timeout) if timeout is not None else self.timeout),
            **options,
            **kwargs,
        )
        if getattr(response, "status", "completed") != "completed":
            return ""
        text = getattr(response, "output_text", "")
        return text.strip() if isinstance(text, str) else ""
