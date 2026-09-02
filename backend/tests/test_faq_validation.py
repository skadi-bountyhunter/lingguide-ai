"""FAQ 字段校验、冲突检测和管理接口测试。"""
import copy

import pytest

from app.api import knowledge


@pytest.fixture
def isolated_faqs(monkeypatch, tmp_path):
    """隔离 FAQ 内存和文件，避免接口测试污染仓库数据。"""
    original = copy.deepcopy(knowledge.FAQ_LIST)
    monkeypatch.setattr(knowledge, "FAQ_LIST", original)
    monkeypatch.setattr(knowledge, "FAQ_FILE", str(tmp_path / "faqs.json"))
    return original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"question": "测试问题", "answer": "测试答案"},
        {
            "question": "测试问题",
            "answer": "测试答案",
            "entities": [],
            "intent": "test",
            "intent_keywords": ["测试"],
        },
        {
            "question": "测试问题",
            "answer": "测试答案",
            "entities": ["测试景点"],
            "intent": "",
            "intent_keywords": ["测试"],
        },
        {
            "question": "测试问题",
            "answer": "测试答案",
            "entities": ["测试景点"],
            "intent": "test",
            "intent_keywords": [],
        },
    ],
)
async def test_create_faq_requires_intent_fields(client, isolated_faqs, payload):
    response = await client.post("/api/knowledge/faqs", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_faq_conflict_does_not_modify_list(client, isolated_faqs):
    before = len(isolated_faqs)
    response = await client.post(
        "/api/knowledge/faqs",
        json={
            "question": "九龙灌浴地点测试",
            "answer": "测试答案",
            "entities": ["九龙灌浴"],
            "intent": "location",
            "intent_keywords": ["表演时间"],
        },
    )
    assert response.status_code == 409
    assert len(knowledge.FAQ_LIST) == before
    assert response.json()["detail"]["code"] == "FAQ_CONFLICT"


@pytest.mark.asyncio
async def test_update_faq_and_not_found(client, isolated_faqs):
    faq_id = isolated_faqs[0]["id"]
    isolated_faqs[0]["exact_questions"] = ["原始精确问法"]
    payload = {
        "question": "更新后的问题",
        "answer": "更新后的答案",
        "entities": ["更新景点"],
        "intent": "updated",
        "intent_keywords": ["更新"],
        "exact_questions": ["原始精确问法"],
    }
    response = await client.put(f"/api/knowledge/faqs/{faq_id}", json=payload)
    assert response.status_code == 200
    assert response.json()["id"] == faq_id
    assert response.json()["intent"] == "updated"
    assert response.json()["exact_questions"] == ["原始精确问法"]

    missing = await client.put("/api/knowledge/faqs/999999", json=payload)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_create_faq_normalizes_and_deduplicates_terms(client, isolated_faqs):
    response = await client.post(
        "/api/knowledge/faqs",
        json={
            "question": "  新 FAQ？ ",
            "answer": "新答案",
            "entities": ["新景点", "新景点"],
            "intent": "new_intent",
            "intent_keywords": ["看点", "看点"],
        },
    )
    assert response.status_code == 200
    assert response.json()["question"] == "新 FAQ？"
    assert response.json()["entities"] == ["新景点"]
    assert response.json()["intent_keywords"] == ["看点"]
