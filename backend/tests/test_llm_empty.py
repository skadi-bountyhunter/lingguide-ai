"""LLM 空响应必须有非空降级或明确异常。"""
from types import SimpleNamespace

import pytest

from app.core import llm
from app.core.llm import LLMGenerationError


class EmptyClient:
    class Chat:
        class Completions:
            async def create(self, **kwargs):
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=None))])

        completions = Completions()

    chat = Chat()


@pytest.mark.asyncio
async def test_empty_content_uses_non_empty_mock(monkeypatch):
    monkeypatch.setattr(llm, "_get_client", lambda: EmptyClient())
    chunks = []
    async for chunk in llm.generate_response("你好", ""):
        chunks.append(chunk)
    assert "".join(chunks).strip()


@pytest.mark.asyncio
async def test_empty_content_without_mock_raises(monkeypatch):
    monkeypatch.setattr(llm, "_get_client", lambda: EmptyClient())
    with pytest.raises(LLMGenerationError):
        async for _ in llm.generate_response("你好", "", allow_mock_fallback=False):
            pass
