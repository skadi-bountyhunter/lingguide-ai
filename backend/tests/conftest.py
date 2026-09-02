"""测试配置和公共 fixtures。"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.api import chat as chat_api
from app.core.database import Base, build_runtime, get_db
from app.core.rag import HybridRAGService, RAG_AVAILABLE, SQLiteLexicalRetriever
from app.main import app
from app.services import chat_service


class FakeEmbedder:
    """确定性嵌入，仅用于隔离集成测试的索引链路验收。"""

    def encode(self, texts, normalize_embeddings=True):
        import hashlib
        import math

        vectors = []
        for text in texts:
            digest = hashlib.sha256(str(text).encode("utf-8")).digest()
            values = [byte / 255 for byte in digest[:8]]
            norm = math.sqrt(sum(value * value for value in values)) or 1
            vectors.append([value / norm for value in values])
        return _EncodedVectors(vectors)


class _EncodedVectors:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values


@pytest.fixture
async def client(tmp_path):
    """异步 HTTP 测试客户端，使用临时 SQLite，避免污染真实数据库。"""
    database_path = tmp_path / "lingguide-test.db"
    engine, session_factory = build_runtime(str(database_path))

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def isolated_get_db():
        async with session_factory() as session:
            yield session

    original_provider = chat_service.db_provider
    original_chat_session = chat_api.async_session
    app.dependency_overrides[get_db] = isolated_get_db
    chat_service.db_provider = isolated_get_db
    chat_api.async_session = session_factory
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        chat_service.db_provider = original_provider
        chat_api.async_session = original_chat_session
        await engine.dispose()


@pytest.fixture
async def isolated_rag_runtime(tmp_path):
    """创建不触碰持久数据的 SQLite + FTS5 + embedded Chroma 运行时。"""
    if not RAG_AVAILABLE:
        pytest.skip("ChromaDB / sentence-transformers 未安装，跳过隔离向量集成测试")

    database_path = tmp_path / "rag-integration.db"
    chroma_path = tmp_path / "chroma"
    engine, session_factory = build_runtime(str(database_path))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    SQLiteLexicalRetriever(str(database_path), ensure_schema=True)
    rag = HybridRAGService(
        sqlite_path=str(database_path),
        chroma_path=str(chroma_path),
        embedder=FakeEmbedder(),
    )
    yield {
        "database_path": database_path,
        "chroma_path": chroma_path,
        "engine": engine,
        "session_factory": session_factory,
        "rag": rag,
    }
    await engine.dispose()


@pytest.fixture
def faq_queries():
    """FAQ 精准匹配测试用例"""
    return [
        ("灵山大佛有多高？", "88米"),
        ("梵宫有什么特色？", "东方卢浮宫"),
        ("九龙灌浴表演时间是？", "10:00"),
        ("景区开放时间", "08:00"),
        ("门票多少钱", "210元"),
        ("灵山大佛什么时候建造的？", "1997"),
        ("五印坛城", "藏传佛教"),
        ("天下第一掌", "祈福"),
        ("祥符禅寺", "唐代"),
        ("怎么去灵山胜境", "88路"),
        ("游览要多长时间", "4-5小时"),
        ("老人小孩适合去吗", "无障碍"),
        ("灵山的历史文化", "太湖之滨"),
        ("纪念品", "福牌"),
        ("好吃的推荐", "素斋"),
    ]


@pytest.fixture
def rag_queries():
    """RAG 检索测试用例（非 FAQ 覆盖的问题）"""
    return [
        "灵山大佛的建造过程是怎样的？",
        "菩提大道有什么特色？",
        "阿育王柱的历史？",
        "百子戏弥勒在什么地方？",
    ]


@pytest.fixture
def clean_tests():
    """回复清理测试用例"""
    from app.core.llm import _clean_response
    return _clean_response
