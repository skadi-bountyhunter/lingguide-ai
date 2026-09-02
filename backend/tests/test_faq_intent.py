"""FAQ 实体与意图联合匹配测试。"""
import pytest

from app.api.chat import match_faq
from app.core.llm import _mock_reply
from app.core.retrieval_types import RAGResult
from app.services.query_coordinator import QueryCoordinator


@pytest.mark.parametrize(
    "query",
    [
        "九龙灌浴在哪里",
        "九龙灌浴有什么寓意",
        "介绍一下九龙灌浴",
        "九龙灌浴好玩吗",
        "九龙灌浴下雨还表演吗",
        "规划一条经过九龙灌浴的路线",
    ],
)
def test_jiulong_non_time_question_does_not_match_time_faq(query):
    assert match_faq(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "九龙灌浴几点表演",
        "九龙灌浴什么时候开始",
        "九龙灌浴每天有几场",
        "九龙灌浴表演时间是？",
    ],
)
def test_jiulong_time_question_matches_time_faq(query):
    faq = match_faq(query)
    assert faq is not None
    assert faq["intent"] == "performance_time"


def test_mock_reply_uses_question_intent():
    location_reply = _mock_reply("九龙灌浴在哪里", "")
    time_reply = _mock_reply("九龙灌浴几点表演", "")

    assert "10:00" not in location_reply
    assert "九龙喷水" in location_reply
    assert "10:00" in time_reply


def _spot(name: str) -> RAGResult:
    return RAGResult(
        content=f"{name}介绍",
        source=name,
        score=1,
        chunk_id=f"spot:{name}",
        document_id=f"spot:{name}",
        source_type="spot",
        content_hash="hash",
        fused_score=1,
    )


def test_named_spot_does_not_use_generic_family_faq():
    coordinator = QueryCoordinator()
    query = "百子戏弥勒适合亲子游吗？"
    faq = match_faq(query)

    assert faq is not None
    assert coordinator._faq_covers_named_spots(query, faq, [_spot("百子戏弥勒")]) is False


def test_multiple_named_spots_do_not_use_single_faq():
    coordinator = QueryCoordinator()
    query = "梵宫和五印坛城分别有什么建筑特色？"
    faq = match_faq(query)

    assert faq is not None
    assert coordinator._faq_covers_named_spots(
        query,
        faq,
        [_spot("梵宫"), _spot("五印坛城")],
    ) is False


def test_single_named_spot_keeps_its_own_faq():
    coordinator = QueryCoordinator()
    query = "梵宫里面有哪些艺术特色？"
    faq = match_faq(query)

    assert faq is not None
    assert coordinator._faq_covers_named_spots(query, faq, [_spot("梵宫")]) is True
