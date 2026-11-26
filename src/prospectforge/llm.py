from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from .config import get_default_model, get_openai_api_key, get_openai_base_url
from .errors import ConfigError, LLMParseError, ProviderError
from .models import Draft, Lead, Qualification
from .prompts import (
    DRAFT_SYSTEM,
    DRAFT_USER_TEMPLATE,
    QUALIFY_SYSTEM,
    QUALIFY_USER_TEMPLATE,
)


def _lead_payload(lead: Lead) -> dict[str, Any]:
    return {
        "key": lead.key,
        "name": lead.name,
        "title": lead.title,
        "company": lead.company,
        "industry": lead.industry,
        "company_size": lead.company_size,
        "country": lead.country,
    }


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMParseError("LLM response did not contain a JSON object.")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMParseError(f"LLM response was not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMParseError("LLM response JSON was not an object.")
    return data


class LLMClient(Protocol):
    def qualify(self, lead: Lead, product: str, icp: str) -> Qualification: ...

    def draft(self, lead: Lead, qualification: Qualification, product: str) -> Draft: ...


class OpenAICompatClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        key = api_key if api_key is not None else get_openai_api_key()
        if not key:
            raise ConfigError("OPENAI_API_KEY is not set.")
        self._api_key = key
        self._base_url = (base_url or get_openai_base_url()).rstrip("/")
        self._model = model or get_default_model()
        self._transport = transport
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def _client(self) -> httpx.Client:
        return httpx.Client(transport=self._transport, timeout=self._timeout)

    def _chat(self, system: str, user: str) -> str:
        payload = {
            "model": self._model,
            "temperature": 0,
            "max_tokens": 300,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            with self._client() as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise LLMParseError("LLM message content was not a string.")
            return content
        except LLMParseError:
            raise
        except Exception as exc:  # noqa: BLE001 - wrap transport/shape failures
            raise ProviderError(f"LLM request failed: {exc}") from exc

    def _chat_json(self, system: str, user: str) -> dict[str, Any]:
        last_error: LLMParseError | None = None
        for _ in range(2):
            content = self._chat(system, user)
            try:
                return _extract_json(content)
            except LLMParseError as exc:
                last_error = exc
        raise last_error or LLMParseError("LLM response could not be parsed.")

    def qualify(self, lead: Lead, product: str, icp: str) -> Qualification:
        context = {
            "key": lead.key,
            "product": product,
            "icp": icp,
            "lead": _lead_payload(lead),
        }
        user = QUALIFY_USER_TEMPLATE % json.dumps(context, ensure_ascii=False)
        data = self._chat_json(QUALIFY_SYSTEM, user)
        try:
            return Qualification(
                lead_key=str(data.get("lead_key") or lead.key),
                score=int(data["score"]),
                verdict=data["verdict"],
                reasons=[str(reason) for reason in data.get("reasons", [])],
                source="llm",
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMParseError(f"LLM qualification JSON was invalid: {exc}") from exc

    def draft(self, lead: Lead, qualification: Qualification, product: str) -> Draft:
        context = {
            "key": lead.key,
            "product": product,
            "lead": _lead_payload(lead),
            "qualification": {
                "score": qualification.score,
                "verdict": qualification.verdict,
                "reasons": qualification.reasons,
            },
        }
        user = DRAFT_USER_TEMPLATE % json.dumps(context, ensure_ascii=False)
        data = self._chat_json(DRAFT_SYSTEM, user)
        try:
            return Draft(
                lead_key=str(data.get("lead_key") or lead.key),
                subject=str(data["subject"]),
                body=str(data["body"]),
                source="llm",
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMParseError(f"LLM draft JSON was invalid: {exc}") from exc
