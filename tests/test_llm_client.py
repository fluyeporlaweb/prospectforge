from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from prospectforge.errors import ConfigError, LLMParseError
from prospectforge.llm import OpenAICompatClient
from prospectforge.models import Lead, Qualification


def _response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": content}}]},
    )


def _client(handler: Any) -> OpenAICompatClient:
    return OpenAICompatClient(
        api_key="test-key-not-real",
        base_url="https://llm.example/v1",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )


def test_valid_qualification_json_is_parsed(sample_lead: Lead) -> None:
    payload = {
        "lead_key": sample_lead.key,
        "score": 80,
        "verdict": "strong",
        "reasons": ["Founder at a software company.", "Located in Spain."],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["temperature"] == 0
        assert body["stream"] is False
        return _response(json.dumps(payload))

    qualification = _client(handler).qualify(sample_lead, "test product", "founders in Spain")
    assert qualification.score == 80
    assert qualification.verdict == "strong"
    assert qualification.source == "llm"


def test_malformed_json_retries_once_then_raises(sample_lead: Lead) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response("not json at all")

    with pytest.raises(LLMParseError):
        _client(handler).qualify(sample_lead, "test product", "founders in Spain")
    assert calls == 2


def test_valid_draft_json_is_parsed(sample_lead: Lead) -> None:
    payload = {"lead_key": sample_lead.key, "subject": "Quick idea", "body": "Hi Sam,"}

    def handler(request: httpx.Request) -> httpx.Response:
        return _response(json.dumps(payload))

    qualification = Qualification(
        lead_key=sample_lead.key,
        score=80,
        verdict="strong",
        reasons=["Fits the ICP."],
        source="heuristic",
    )
    draft = _client(handler).draft(sample_lead, qualification, "test product")
    assert draft.subject == "Quick idea"
    assert draft.source == "llm"


def test_missing_api_key_is_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        OpenAICompatClient()


def test_api_key_is_not_echoed_in_errors() -> None:
    secret = "test-key-not-real"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = OpenAICompatClient(
        api_key=secret,
        base_url="https://llm.example/v1",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(Exception) as exc_info:
        client.qualify(Lead(name="A", email="a@example.com"), "p", "i")
    assert secret not in str(exc_info.value)


def test_llm_qualifier_falls_back_to_heuristic(sample_lead: Lead) -> None:
    from prospectforge.qualify import LLMQualifier

    class BrokenClient:
        def qualify(self, lead, product, icp):
            raise LLMParseError("bad output")

        def draft(self, lead, qualification, product):
            raise LLMParseError("bad output")

    qualification = LLMQualifier(BrokenClient()).qualify(
        sample_lead, "test product", "founders in Spain"
    )
    assert qualification.source == "heuristic"
    assert qualification.reasons
