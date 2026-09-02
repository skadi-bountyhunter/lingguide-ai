"""个人中心后端专项测试。"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models import Interaction, User
from app.models.feedback import Feedback
from app.models.notification import Notification
from app.models.favorite import Favorite

PHONE_A = "13800000001"
PHONE_B = "13800000002"
TOKEN_A = f"token_{PHONE_A}"
TOKEN_B = f"token_{PHONE_B}"


@pytest_asyncio.fixture
async def profile_client(tmp_path):
    """使用双用户临时 SQLite，避免污染演示库。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'profile.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        session.add_all(
            [
                User(id=uuid.uuid4().hex, phone=PHONE_A, password="password-a", nickname="用户甲"),
                User(id=uuid.uuid4().hex, phone=PHONE_B, password="password-b", nickname="用户乙"),
            ]
        )
        await session.commit()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client, session_factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": token}


@pytest.mark.asyncio
async def test_favorites_are_typed_owned_and_return_record_id(profile_client):
    client, _ = profile_client
    response = await client.post(
        "/api/profile/favorites",
        headers=headers(TOKEN_A),
        json={"item_type": "spot", "item_id": "1", "item_name": "灵山大佛"},
    )
    assert response.status_code == 201
    favorite_id = response.json()["id"]
    assert isinstance(favorite_id, int)
    assert (await client.get(
        "/api/profile/favorites/check/1?item_type=spot", headers=headers(TOKEN_A)
    )).json() == {"favorited": True, "id": favorite_id}
    assert (await client.get(
        "/api/profile/favorites/check/1?item_type=route", headers=headers(TOKEN_A)
    )).json() == {"favorited": False, "id": None}
    async with profile_client[1]() as session:
        session.add(
            Favorite(
                user_id="anonymous",
                item_type="spot",
                item_id="legacy",
                item_name="旧匿名收藏",
            )
        )
        await session.commit()
    assert (await client.get(
        "/api/profile/favorites", headers=headers(TOKEN_B)
    )).json() == []
    assert (await client.delete(
        f"/api/profile/favorites/{favorite_id}", headers=headers(TOKEN_B)
    )).status_code == 404
    assert (await client.delete(
        f"/api/profile/favorites/{favorite_id}", headers=headers(TOKEN_A)
    )).status_code == 200


@pytest.mark.asyncio
async def test_profile_stats_and_visits_are_real_and_isolated(profile_client):
    client, session_factory = profile_client
    await client.post(
        "/api/profile/visits",
        headers=headers(TOKEN_A),
        json={"item_type": "spot", "item_id": "1", "item_name": "灵山大佛"},
    )
    visit = await client.post(
        "/api/profile/visits",
        headers=headers(TOKEN_A),
        json={"item_type": "spot", "item_id": "1", "item_name": "灵山大佛"},
    )
    assert visit.json()["visit_count"] == 2
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.phone == PHONE_A))
        session.add(
            Interaction(
                id=uuid.uuid4().hex,
                user_id=user.id,
                session_id="profile-session",
                query_text="问题",
                response_text="回答",
            )
        )
        await session.commit()
    profile = await client.get("/api/profile/me", headers=headers(TOKEN_A))
    assert profile.status_code == 200
    assert profile.json()["nickname"] == "用户甲"
    assert profile.json()["phone"] == "138****0001"
    assert profile.json()["stats"]["visit_count"] == 2
    assert profile.json()["stats"]["interaction_count"] == 1
    assert (await client.get("/api/profile/visits", headers=headers(TOKEN_B))).json() == []


@pytest.mark.asyncio
async def test_feedback_reset_and_notifications(profile_client):
    client, session_factory = profile_client
    feedback = await client.post(
        "/api/profile/feedback",
        headers=headers(TOKEN_A),
        json={"category": "suggestion", "content": "建议增加路线提示"},
    )
    assert feedback.status_code == 201
    assert (await client.get(
        "/api/profile/feedback", headers=headers(TOKEN_B)
    )).json() == []
    async with session_factory() as session:
        user_a = await session.scalar(select(User).where(User.phone == PHONE_A))
        user_b = await session.scalar(select(User).where(User.phone == PHONE_B))
        session.add_all(
            [
                Notification(title="全体", content="公告", category="system"),
                Notification(
                    title="个人", content="仅甲可见", category="service", target_user_id=user_a.id
                ),
            ]
        )
        user_b.role = "admin"
        session.add(user_b)
        await session.commit()
    notices_a = await client.get("/api/profile/notifications", headers=headers(TOKEN_A))
    notices_b = await client.get("/api/profile/notifications", headers=headers(TOKEN_B))
    assert {item["title"] for item in notices_a.json()} == {"全体", "个人"}
    assert {item["title"] for item in notices_b.json()} == {"全体"}
    notification_id = next(item["id"] for item in notices_a.json() if item["title"] == "个人")
    marked = await client.patch(
        f"/api/profile/notifications/{notification_id}/read", headers=headers(TOKEN_A)
    )
    assert marked.json()["unread_count"] == 1


@pytest.mark.asyncio
async def test_reset_password_is_one_time(profile_client):
    client, session_factory = profile_client
    from app.api.auth import _verify_codes

    _verify_codes[PHONE_A] = "123456"
    response = await client.post(
        "/api/auth/reset-password",
        json={"phone": PHONE_A, "verify_code": "123456", "new_password": "new-pass"},
    )
    assert response.status_code == 200
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.phone == PHONE_A))
        assert user.password == "new-pass"
    replay = await client.post(
        "/api/auth/reset-password",
        json={"phone": PHONE_A, "verify_code": "123456", "new_password": "again-pass"},
    )
    assert replay.status_code == 400
