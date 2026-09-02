"""灵境导游运行配置。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = Path(__file__).resolve().parents[1]
SCENIC_WEATHER_CITY = "灵山胜境"
SCENIC_WEATHER_SCOPE = "无锡"
SCENIC_WEATHER_ADCODE = "320211"


class Settings(BaseSettings):
    """应用全局配置。"""

    # --- 运行模式 ---
    runtime_mode: str = Field(default="development", validation_alias="RUNTIME_MODE")
    resource_root: str = Field(
        default=str(_BACKEND_DIR),
        validation_alias="LINGGUIDE_RESOURCE_ROOT",
    )
    data_root: str = Field(
        default=str(_BACKEND_DIR / "app" / "data"),
        validation_alias=AliasChoices("DATA_ROOT", "LINGGUIDE_DATA_ROOT"),
    )
    rag_mode: str = Field(default="full", validation_alias="RAG_MODE")
    desktop_origin: str = Field(default="", validation_alias="LINGGUIDE_DESKTOP_ORIGIN")
    admin_token: str = Field(default="", validation_alias="LINGGUIDE_ADMIN_TOKEN")

    # --- 应用 ---
    app_secret_key: str = "change-me"
    app_debug: bool = True
    app_port: int = 8000

    # --- 数据库 ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "lingguide"
    postgres_user: str = "lingguide"
    postgres_password: str = "lingguide123"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379

    # --- ChromaDB ---
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # --- LLM ---
    llm_provider: str = "local"
    llm_model: str = "Qwen/Qwen3-8B"
    llm_base_url: str = "http://localhost:8002/v1"
    llm_api_key: str = "not-needed"
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"

    # --- 高德开放平台 ---
    amap_web_key: Optional[str] = None

    # --- Embedding ---
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    embedding_allow_download: bool = False
    hf_endpoint: str = "https://hf-mirror.com"

    # --- ASR ---
    asr_provider: str = "iflytek"
    whisper_model: str = "large-v3"
    whisper_device: str = "cpu"
    iflytek_app_id: str = ""
    iflytek_api_key: str = ""
    iflytek_api_secret: str = ""

    # --- 语音情感识别 ---
    aliyun_access_key_id: str = ""
    aliyun_access_key_secret: str = ""
    aliyun_nls_app_key: str = ""
    dashscope_api_key: str = ""

    # --- TTS ---
    tts_provider: str = "edge"
    cosyvoice_url: str = "http://localhost:5001"

    # --- 魔珐星云数字人 ---
    xingyun_default_guide_app_id: str = ""
    xingyun_default_guide_app_secret: str = ""
    xingyun_gateway_url: str = "https://nebula-agent.xingyun3d.com/user/v1/ttsa/session"
    xingyun_preset_credentials: str = ""

    # --- 文件存储与浏览器安全 ---
    upload_dir: str = "./uploads"
    faq_path: str = str(_BACKEND_DIR / "app" / "faqs.json")
    log_path: str = str(_BACKEND_DIR / "logs" / "lingguide.log")
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    websocket_allowed_origins: str = "http://localhost:3000,http://localhost:3001"
    websocket_require_origin: bool = False
    websocket_max_message_bytes: int = 64 * 1024
    websocket_rate_limit_per_minute: int = 30
    websocket_max_connections_per_ip: int = 5
    websocket_max_messages_per_connection: int = 60
    websocket_max_concurrent_messages: int = 2
    websocket_receive_timeout_seconds: float = 120.0
    websocket_send_timeout_seconds: float = 10.0
    websocket_retrieval_timeout_seconds: float = 8.0
    websocket_llm_timeout_seconds: float = 45.0

    # --- 生产检索与服务超时 ---
    retrieval_timeout_seconds: float = 8.0
    llm_timeout_seconds: float = 45.0
    weather_timeout_seconds: float = 8.0
    weather_geocode_timeout_seconds: float = 2.5
    weather_forecast_timeout_seconds: float = 3.0
    weather_live_timeout_seconds: float = 2.5
    weather_cache_ttl_seconds: float = 300.0
    weather_stale_window_seconds: float = 900.0
    weather_cache_max_entries: int = 128
    weather_default_city: str = SCENIC_WEATHER_CITY
    weather_default_scope: str = SCENIC_WEATHER_SCOPE
    weather_default_adcode: str = SCENIC_WEATHER_ADCODE
    readiness_strict: bool = True

    # --- SQLite + embedded Chroma ---
    sqlite_path: str = "./app/data/lingguide.db"
    chroma_path: str = "./app/chroma_store"

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    @field_validator("runtime_mode")
    @classmethod
    def validate_runtime_mode(cls, value: str) -> str:
        normalized = str(value or "development").strip().lower()
        if normalized not in {"development", "desktop"}:
            raise ValueError("RUNTIME_MODE 仅支持 development 或 desktop")
        return normalized

    @field_validator("rag_mode")
    @classmethod
    def validate_rag_mode(cls, value: str) -> str:
        normalized = str(value or "full").strip().lower()
        if normalized not in {"full", "lite"}:
            raise ValueError("RAG_MODE 仅支持 full 或 lite")
        return normalized

    @field_validator("amap_web_key", mode="before")
    @classmethod
    def normalize_amap_web_key(cls, value: object) -> str | None:
        """把空白高德 Key 视为未配置。"""
        normalized = str(value or "").strip()
        return normalized or None

    @model_validator(mode="after")
    def apply_runtime_contract(self) -> "Settings":
        """便携模式的所有可写文件固定到 DATA_ROOT。"""
        if self.runtime_mode == "desktop":
            data_root = Path(self.data_root).expanduser()
            if not data_root.is_absolute():
                executable_dir = Path(sys.executable).resolve().parent
                data_root = executable_dir / data_root
            data_root = data_root.resolve()
            self.data_root = str(data_root)
            self.resource_root = str(Path(self.resource_root).expanduser().resolve())
            self.app_debug = False
            self.sqlite_path = str(data_root / "lingguide.db")
            self.upload_dir = str(data_root / "uploads")
            self.chroma_path = str(data_root / "chroma")
            self.faq_path = str(data_root / "faqs.json")
            self.log_path = str(data_root / "logs" / "lingguide.log")
            self.cors_origins = self.desktop_origin
            self.websocket_allowed_origins = self.desktop_origin
            self.websocket_require_origin = True
        return self

    @model_validator(mode="after")
    def validate_scenic_weather_location(self) -> "Settings":
        """景区天气必须固定到无锡灵山，防止环境变量导致地点漂移。"""
        configured = (
            self.weather_default_city.strip(),
            self.weather_default_scope.strip(),
            self.weather_default_adcode.strip(),
        )
        expected = (SCENIC_WEATHER_CITY, SCENIC_WEATHER_SCOPE, SCENIC_WEATHER_ADCODE)
        if configured != expected:
            raise ValueError("景区天气配置必须固定为无锡灵山胜境（adcode 320211）")
        return self

    @property
    def is_desktop(self) -> bool:
        return self.runtime_mode == "desktop"

    @property
    def is_lite(self) -> bool:
        return self.rag_mode == "lite"


# 便携模式禁止隐式读取开发目录中的 .env。
settings = Settings(
    _env_file=None if os.getenv("RUNTIME_MODE", "development").strip().lower() == "desktop" else str(_BACKEND_DIR / ".env")
)


def resolve_runtime_path(value: str) -> str:
    """开发路径相对 backend，便携路径由配置提前解析为 DATA_ROOT。"""
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = _BACKEND_DIR / path
    return str(path.resolve())


def resolve_resource_path(*parts: str) -> str:
    """按统一契约读取 RESOURCE_ROOT 下的只读发布资源。"""
    return str((Path(settings.resource_root).resolve().joinpath(*parts)).resolve())


if settings.hf_endpoint:
    os.environ["HF_ENDPOINT"] = settings.hf_endpoint
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
