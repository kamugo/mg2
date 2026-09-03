"""Zero-shot and few-shot adapter for an OpenAI-compatible chat endpoint."""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Mapping, Sequence


class LLMCoreferenceAdapter:
    """Request schema-constrained antecedent decisions without a client dependency."""

    def __init__(
        self,
        model: str,
        endpoint: str,
        api_key_env: str = "COREFERENCE_LLM_API_KEY",
        timeout_seconds: int = 60,
    ) -> None:
        self.model = model
        self.endpoint = endpoint
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds

    def predict(
        self,
        text: str,
        mentions: Sequence[Mapping[str, object]],
        demonstrations: Sequence[Mapping[str, object]] = (),
    ) -> dict[str, object]:
        """Call the API with optional few-shot demonstrations and return parsed JSON."""
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key in {self.api_key_env}.")
        instruction = (
            "Resolve Polish legal-text coreference. Return JSON with a decisions array. "
            "Each decision must contain mention_id and antecedent_id or null. "
            "Use only identifiers supplied in the input."
        )
        messages: list[dict[str, str]] = [{"role": "system", "content": instruction}]
        for example in demonstrations:
            messages.extend(
                [
                    {"role": "user", "content": json.dumps(example["input"], ensure_ascii=False)},
                    {"role": "assistant", "content": json.dumps(example["output"], ensure_ascii=False)},
                ]
            )
        messages.append(
            {
                "role": "user",
                "content": json.dumps({"text": text, "mentions": mentions}, ensure_ascii=False),
            }
        )
        payload = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": messages,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
