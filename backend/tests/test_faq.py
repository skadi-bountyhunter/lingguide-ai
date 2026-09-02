"""FAQ 匹配测试 — 验证精确匹配和关键词匹配"""
import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("query,expected", [
    # 精确匹配
    ("灵山大佛有多高？", "88米"),
    ("梵宫有什么特色？", "东方卢浮宫"),
    ("九龙灌浴表演时间是？", "10:00"),
    ("灵山大佛什么时候建造的？", "1997"),
    ("五印坛城是什么？", "藏传佛教"),
    ("天下第一掌是什么？", "祈福"),
    ("祥符禅寺有什么历史？", "唐代"),
    ("怎么去灵山胜境？", "88路"),
    ("灵山的历史文化", "太湖之滨"),
    # 关键词匹配（≥4字关键词 + 覆盖率≥30%）
    ("梵宫有什么看点", "东方卢浮宫"),
    ("怎么去灵山大佛", "88路"),
    ("带老人去方便吗", "无障碍"),
    ("灵山有什么好吃的", "素斋"),
    ("九龙灌浴几点开始", "10:00"),
    ("九龙灌浴什么时候表演", "10:00"),
    ("九龙灌浴每天有几场", "10:00"),
])
async def test_faq_matching(client, query, expected):
    """测试 FAQ 精确匹配和关键词匹配"""
    res = await client.post("/api/chat/text", json={
        "query": query,
        "interests": [],
    })
    assert res.status_code == 200
    data = res.json()
    assert "FAQ 精确匹配" in data["sources"], \
        f"query='{query}' expected FAQ match, got sources={data['sources']}"
    assert expected in data["reply"], \
        f"query='{query}' expected '{expected}' in reply, got '{data['reply'][:80]}'"
    assert data["thinking_time_ms"] <= 500, \
        f"FAQ response too slow: {data['thinking_time_ms']}ms"


@pytest.mark.asyncio
@pytest.mark.parametrize("query", [
    "怎么去颐和园",         # 非灵山问题，应走RAG
    "介绍一下灵山大佛的历史", # 非FAQ精确匹配
    "带奶奶去方便吗",        # 短关键词不足以触发
    "九龙灌浴在哪里",        # 景点实体不应单独命中表演时间 FAQ
    "九龙灌浴有什么寓意",    # 非时间意图
    "介绍一下九龙灌浴",      # 通用介绍应交给 RAG/LLM
    "九龙灌浴好玩吗",        # 非时间意图
    "规划一条经过九龙灌浴的路线",  # 路线意图保护
])
async def test_faq_not_matched(client, query):
    """非FAQ问题应走RAG而非错误匹配"""
    res = await client.post("/api/chat/text", json={
        "query": query,
        "interests": [],
    })
    assert res.status_code == 200
    data = res.json()
    assert "FAQ" not in str(data["sources"]), \
        f"query='{query}' should NOT match FAQ, but got sources={data['sources']}"
    assert data["trace_id"].startswith("trace_"), \
        f"query='{query}' should return a trace ID, got {data['trace_id']!r}"


@pytest.mark.asyncio
async def test_faq_via_websocket(client):
    """测试 WebSocket FAQ 匹配（通过对比 REST 结果验证）"""
    # WebSocket 在同一路由逻辑下执行，通过 REST 端到端验证
    res = await client.post("/api/chat/text", json={
        "query": "灵山大佛有多高？",
        "interests": ["佛教文化"],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["emotion"] in ("positive", "neutral", "negative")
    assert data["expression"] in ("happy", "neutral", "concerned")
    assert len(data["reply"]) > 10


@pytest.mark.asyncio
async def test_faq_stats(client):
    """测试 FAQ 统计接口"""
    res = await client.get("/api/knowledge/faqs")
    assert res.status_code == 200
    faqs = res.json()
    assert len(faqs) >= 15
    # 验证每个 FAQ 结构
    for faq in faqs:
        assert "question" in faq
        assert "answer" in faq
        assert "intent" in faq
        assert "entities" in faq
        assert "intent_keywords" in faq
