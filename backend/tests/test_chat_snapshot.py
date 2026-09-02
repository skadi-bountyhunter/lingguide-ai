"""对话路线快照的判定和顺序测试。"""
from app.api.chat import RouteResponse, RouteSpot, _is_route_request, _route_plan_payload


def test_route_intent_requires_planning_semantics():
    assert _is_route_request("请规划一条先去梵宫再去九龙灌浴的路线")
    assert _is_route_request("推荐一条半天游路线")
    assert not _is_route_request("介绍一下路线上的梵宫")
    assert not _is_route_request("九龙灌浴表演时间是几点")


def test_route_snapshot_preserves_response_order():
    route = RouteResponse(
        title="测试路线",
        duration="约4小时",
        spots=[
            RouteSpot(name="梵宫", description="艺术殿堂"),
            RouteSpot(name="九龙灌浴", description="精彩表演"),
        ],
        tips="错峰游览",
        sources=["知识库"],
    )
    snapshot = _route_plan_payload(route, ["建筑艺术"], "半天")
    assert snapshot["schema_version"] == 1
    assert [spot["name"] for spot in snapshot["spots"]] == ["梵宫", "九龙灌浴"]
    assert snapshot["duration_mode"] == "半天"
