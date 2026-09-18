"""Optional OpenAI adapter; extractive mode needs no SDK or API key."""

import os
from typing import Any

from .prompts import SYSTEM_PROMPT


class AnswerGenerator:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: Any = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL") or "gpt-5.6"
        self.client = client
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return self.client is not None or bool(self.api_key.strip())

    def generate(self, prompt: str, *, instructions: str | None = None) -> str:
        if not self.available:
            return ""
        if self.client is None:
            from openai import OpenAI

            self.client = OpenAI(
                api_key=self.api_key, timeout=self.timeout, max_retries=0
            )
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions if instructions is not None else SYSTEM_PROMPT,
            input=prompt,
            max_output_tokens=2000,
            store=False,
        )
        if getattr(response, "status", "completed") != "completed":
            return ""
        text = getattr(response, "output_text", "")
        return text.strip() if isinstance(text, str) else ""
