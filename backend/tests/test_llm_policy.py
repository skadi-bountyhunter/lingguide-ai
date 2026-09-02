"""LLM 总 deadline、有限重试和诊断脱敏回归测试。"""
from types import SimpleNamespace

import httpx
import pytest

from app.config import settings
from app.core import llm
from app.core.llm import LLMExecutionReport, LLMGenerationError
from app.api.rag_admin import _trace_text_summary


class FakeClient:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    class Chat:
        pass

    async def _create(self, **_kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    @property
    def chat(self):
        return SimpleNamespace(completions=SimpleNamespace(create=self._create))


def response(text="生成成功"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text, tool_calls=None))]
    )


@pytest.fixture
def llm_settings(monkeypatch):
    monkeypatch.setattr(settings, "llm_timeout_seconds", 0.2)
    monkeypatch.setattr(settings, "llm_provider", "local")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    monkeypatch.setattr(llm, "_get_client", lambda: None)


@pytest.mark.asyncio
async def test_retryable_timeout_retries_once_then_succeeds(monkeypatch, llm_settings):
    client = FakeClient([httpx.ReadTimeout("temporary"), response()])
    monkeypatch.setattr(llm, "_get_client", lambda: client)
    report = LLMExecutionReport()

    chunks = [
        chunk
        async for chunk in llm.generate_response(
            "问题", "证据", allow_mock_fallback=False, report=report
        )
    ]

    assert chunks == ["生成成功"]
    assert client.calls == 2
    assert report.status == "ok"
    assert report.attempt_count == 2
    assert report.retry_count == 1
    assert report.error_category is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 401, 403, 404])
async def test_non_retryable_http_error_does_not_retry(monkeypatch, llm_settings, status_code):
    error = RuntimeError("provider detail must not leak")
    error.status_code = status_code
    client = FakeClient([error, response()])
    monkeypatch.setattr(llm, "_get_client", lambda: client)
    report = LLMExecutionReport()

    with pytest.raises(LLMGenerationError) as caught:
        async for _ in llm.generate_response(
            "敏感问题", "敏感证据", allow_mock_fallback=False, report=report
        ):
            pass

    assert client.calls == 1
    assert caught.value.category == "http_4xx"
    assert "provider detail" not in str(caught.value)
    assert report.retry_count == 0


@pytest.mark.asyncio
async def test_total_deadline_stops_slow_model_call(monkeypatch, llm_settings):
    async def slow_create(**_kwargs):
        await __import__("asyncio").sleep(1)

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=slow_create))
    )
    monkeypatch.setattr(llm, "_get_client", lambda: client)
    monkeypatch.setattr(settings, "llm_timeout_seconds", 0.01)
    report = LLMExecutionReport()

    with pytest.raises(LLMGenerationError) as caught:
        async for _ in llm.generate_response(
            "问题", "证据", allow_mock_fallback=False, report=report
        ):
            pass

    assert caught.value.category == "deadline_exceeded"
    assert report.error_category == "deadline_exceeded"
    assert report.attempt_count == 1


def test_trace_text_summary_never_returns_original_text():
    summary = _trace_text_summary("游客的完整问题和回答")

    assert summary["length"] == 10
    assert "游客的完整问题和回答" not in summary.values()
    assert len(summary["sha256"]) == 64
