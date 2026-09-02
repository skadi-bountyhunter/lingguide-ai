"""WebSocket 事件链与会话边界测试。"""
import asyncio
import json
import time

import pytest
from starlette.testclient import TestClient

from app.api import chat as chat_api
from app.main import app


@pytest.fixture
def websocket_client():
    """使用同步 TestClient 验证 FastAPI WebSocket 协议。"""
    chat_api._ws_connections_by_ip.clear()
    chat_api._ws_rate_windows.clear()
    chat_api._ws_session_tokens.clear()
    with TestClient(app) as client:
        yield client
    chat_api._ws_connections_by_ip.clear()
    chat_api._ws_rate_windows.clear()
    chat_api._ws_session_tokens.clear()


def _events(ws, payload, count=5):
    ws.send_json(payload)
    received = []
    for _ in range(count):
        received.append(ws.receive_json())
        if received[-1]["type"] in {"message_done", "error"}:
            break
    return received


def test_websocket_requires_session_token(websocket_client):
    with websocket_client.websocket_connect("/api/chat/ws/session-a") as ws:
        ws.send_json({"query": "灵山大佛有多高？"})
        with pytest.raises(Exception):
            ws.receive_json()


def test_websocket_event_chain_and_ids(websocket_client, monkeypatch):
    monkeypatch.setattr(chat_api.settings, "websocket_require_origin", False)
    with websocket_client.websocket_connect("/api/chat/ws/session-a") as ws:
        ws.send_json({"session_token": "token-session-a-123456"})
        events = _events(ws, {"query": "灵山大佛有多高？", "mode": "text"})

    assert [event["type"] for event in events] == [
        "rag_started", "rag_done", "llm_stream", "llm_done", "message_done",
    ]
    request_ids = {event["request_id"] for event in events}
    message_ids = {event["message_id"] for event in events}
    trace_ids = {event["trace_id"] for event in events}
    assert len(request_ids) == len(message_ids) == len(trace_ids) == 1
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
    assert events[-1]["citations"]
    assert events[-1]["retrieval"]


def test_websocket_timeout_finishes_without_candidate_citations(websocket_client, monkeypatch):
    async def retrieve_async(*_args, **_kwargs):
        from app.core.retrieval_types import RAGResult
        from app.services.query_coordinator import QueryResult

        return QueryResult([
            RAGResult(
                content="灵山大佛是景区核心景点。",
                source="景区资料.docx",
                score=0.9,
                chunk_id="chunk-1",
                document_id="doc-1",
                content_hash="hash-1",
                fused_score=0.9,
            )
        ], route="hybrid")

    async def slow_answer(*_args, **_kwargs):
        await asyncio.sleep(5)
        return "不应返回"

    async def get_history(*_args, **_kwargs):
        return []

    async def log(*_args, **_kwargs):
        return None

    monkeypatch.setattr(chat_api.query_coordinator, "retrieve_async", retrieve_async)
    monkeypatch.setattr(chat_api, "generate_answer", slow_answer)
    monkeypatch.setattr(chat_api, "get_session_history", get_history)
    monkeypatch.setattr(chat_api, "log_interaction", log)
    monkeypatch.setattr(chat_api.settings, "websocket_require_origin", False)
    monkeypatch.setattr(chat_api.settings, "websocket_llm_timeout_seconds", 0)

    with websocket_client.websocket_connect("/api/chat/ws/session-timeout") as ws:
        ws.send_json({"session_token": "token-session-timeout-123456"})
        events = _events(ws, {"query": "介绍灵山大佛", "mode": "text"})

    final_event = events[-1]
    assert [event["type"] for event in events] == [
        "rag_started", "rag_done", "llm_stream", "llm_done", "message_done",
    ]
    assert final_event["reply_text"] == chat_api.NO_EVIDENCE_REPLY
    assert final_event["sources"] == []
    assert final_event["citations"] == []
    assert final_event["retrieval"]["degraded"] is True
    assert "llm_deadline_exceeded" in final_event["retrieval"]["fallback_reason"]


def test_websocket_rejects_oversized_message(websocket_client, monkeypatch):
    monkeypatch.setattr(chat_api.settings, "websocket_max_message_bytes", 32)
    with websocket_client.websocket_connect("/api/chat/ws/session-b") as ws:
        ws.send_json({"session_token": "token-session-b-123456"})
        ws.send_json({"query": "x" * 100})
        with pytest.raises(Exception):
            ws.receive_json()


def test_websocket_rejects_invalid_origin_when_required(websocket_client, monkeypatch):
    monkeypatch.setattr(chat_api.settings, "websocket_require_origin", True)
    with pytest.raises(Exception):
        with websocket_client.websocket_connect(
            "/api/chat/ws/session-c",
            headers={"origin": "http://evil.example"},
        ):
            pass


def test_websocket_rejects_missing_origin_when_required(websocket_client, monkeypatch):
    monkeypatch.setattr(chat_api.settings, "websocket_require_origin", True)
    with pytest.raises(Exception):
        with websocket_client.websocket_connect("/api/chat/ws/session-c"):
            pass


def test_websocket_accepts_unlisted_origin_when_check_disabled(websocket_client, monkeypatch):
    monkeypatch.setattr(chat_api.settings, "websocket_require_origin", False)
    with websocket_client.websocket_connect(
        "/api/chat/ws/session-origin-disabled",
        headers={"origin": "http://127.0.0.1:3000"},
    ) as ws:
        ws.send_json({"session_token": "token-origin-disabled-123456"})


def test_websocket_session_token_cannot_change(websocket_client):
    with websocket_client.websocket_connect("/api/chat/ws/session-d") as first:
        first.send_json({"session_token": "token-session-d-123456"})
        with websocket_client.websocket_connect("/api/chat/ws/session-d") as second:
            second.send_json({"session_token": "different-token-123456"})
            with pytest.raises(Exception):
                second.receive_json()


def test_websocket_disconnect_cancels_message_task(websocket_client, monkeypatch):
    cancelled = asyncio.Event()

    async def slow_retrieve(*args, **kwargs):
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    monkeypatch.setattr(chat_api.query_coordinator, "retrieve_async", slow_retrieve)
    with websocket_client.websocket_connect("/api/chat/ws/session-e") as ws:
        ws.send_json({"session_token": "token-session-e-123456"})
        ws.send_json({"query": "测试断线取消"})
        ws.receive_json()
        ws.close()
    deadline = time.time() + 1
    while (chat_api._ws_connections_by_ip or not cancelled.is_set()) and time.time() < deadline:
        time.sleep(0.01)
    assert cancelled.is_set()
    assert not chat_api._ws_connections_by_ip
