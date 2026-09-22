from __future__ import annotations

from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from .config import Settings

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class StructuredOpenAIClient:
    """Small adapter around Responses API structured outputs."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            max_retries=settings.openai_max_retries,
            timeout=settings.openai_timeout_seconds,
        )

    def parse(self, system_prompt: str, user_prompt: str, response_model: type[ResponseT]) -> ResponseT:
        response = self.client.responses.parse(
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=response_model,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError(f"OpenAI returned no parsed output (response id: {response.id})")
        return parsed
