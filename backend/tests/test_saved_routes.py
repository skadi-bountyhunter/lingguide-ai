"""账号保存路线 API 专项测试"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models import User

PHONE_A = "13800000001"
PHONE_B = "13800000002"
TOKEN_A = f"token_{PHONE_A}"
TOKEN_B = f"token_{PHONE_B}"


@pytest_asyncio.fixture
async def saved_routes_client(tmp_path):
    """使用临时 SQLite 隔离保存路线测试。"""
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'saved_routes.db'}"
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        session.add_all(
            [
                User(
                    id=uuid.uuid4().hex,
                    phone=PHONE_A,
                    password="password-a",
                    nickname="用户甲",
                ),
                User(
                    id=uuid.uuid4().hex,
                    phone=PHONE_B,
                    password="password-b",
                    nickname="用户乙",
                ),
            ]
        )
        await session.commit()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": token}


def route_payload(title: str = "禅意路线") -> dict:
    return {
        "source": "chat",
        "title": title,
        "duration": " 3小时 ",
        "spots": [
            {"name": " 灵山大佛 ", "description": " 登高祈福 "},
            {"name": " 梵宫 ", "description": " 欣赏建筑艺术 "},
        ],
        "tips": " 建议上午入园 ",
        "interests": [" 佛教文化 ", " 建筑艺术 "],
    }


@pytest.mark.asyncio
async def test_requires_authorization(saved_routes_client):
    response = await saved_routes_client.get("/api/profile/routes")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_accepts_raw_and_case_insensitive_bearer_tokens(saved_routes_client):
    raw_response = await saved_routes_client.get(
        "/api/profile/routes", headers=auth(TOKEN_A)
    )
    bearer_response = await saved_routes_client.get(
        "/api/profile/routes", headers=auth(f"bEaReR {TOKEN_A}")
    )

    assert raw_response.status_code == 200
    assert bearer_response.status_code == 200


@pytest.mark.asyncio
async def test_chinese_snapshot_and_order(saved_routes_client):
    first = await saved_routes_client.post(
        "/api/profile/routes",
        headers=auth(TOKEN_A),
        json=route_payload(" 第一条路线 "),
    )
    second = await saved_routes_client.post(
        "/api/profile/routes",
        headers=auth(f"Bearer {TOKEN_A}"),
        json=route_payload(" 第二条路线 "),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    first_body = first.json()
    assert first_body == {
        "id": first_body["id"],
        "source": "chat",
        "title": "第一条路线",
        "duration": "3小时",
        "spots": [
            {"name": "灵山大佛", "description": "登高祈福"},
            {"name": "梵宫", "description": "欣赏建筑艺术"},
        ],
        "tips": "建议上午入园",
        "interests": ["佛教文化", "建筑艺术"],
        "created_at": first_body["created_at"],
    }

    response = await saved_routes_client.get(
        "/api/profile/routes", headers=auth(TOKEN_A)
    )
    assert response.status_code == 200
    routes = response.json()
    assert [route["title"] for route in routes] == ["第二条路线", "第一条路线"]
    assert [route["id"] for route in routes] == [second.json()["id"], first.json()["id"]]


@pytest.mark.asyncio
async def test_rejects_empty_spots(saved_routes_client):
    payload = route_payload()
    payload["spots"] = [{"name": "   ", "description": "空景点"}]

    response = await saved_routes_client.post(
        "/api/profile/routes", headers=auth(TOKEN_A), json=payload
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_users_are_isolated_and_cannot_delete_others_route(saved_routes_client):
    created = await saved_routes_client.post(
        "/api/profile/routes", headers=auth(TOKEN_A), json=route_payload()
    )
    route_id = created.json()["id"]

    user_b_list = await saved_routes_client.get(
        "/api/profile/routes", headers=auth(TOKEN_B)
    )
    forbidden_delete = await saved_routes_client.delete(
        f"/api/profile/routes/{route_id}", headers=auth(TOKEN_B)
    )

    assert user_b_list.status_code == 200
    assert user_b_list.json() == []
    assert forbidden_delete.status_code == 404


@pytest.mark.asyncio
async def test_owner_can_delete_route(saved_routes_client):
    created = await saved_routes_client.post(
        "/api/profile/routes", headers=auth(TOKEN_A), json=route_payload()
    )
    route_id = created.json()["id"]

    deleted = await saved_routes_client.delete(
        f"/api/profile/routes/{route_id}", headers=auth(TOKEN_A)
    )
    remaining = await saved_routes_client.get(
        "/api/profile/routes", headers=auth(TOKEN_A)
    )

    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": route_id}
    assert remaining.json() == []
