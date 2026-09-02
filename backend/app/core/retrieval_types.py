"""检索、证据、引用和检索轨迹的数据契约。"""
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


EvidenceKind = Literal["faq", "spot", "route", "document", "weather", "tool"]


@dataclass
class Evidence:
    """统一证据对象；只有 canonical 且有效的证据才能进入回答上下文。"""

    id: str
    kind: EvidenceKind = "document"
    content: str = ""
    source: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    quality_reason: str = ""
    provider: str | None = None
    tool_call_id: str | None = None
    as_of: str | None = None
    expires_at: str | None = None
    status: str = "ready"
    canonical: bool = True
    index_version: str = "legacy-v1"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RAGResult:
    """兼容旧调用方的检索结果，并携带多路召回诊断信息。"""

    content: str
    source: str
    score: float
    chunk_id: str = ""
    document_id: str = ""
    source_type: str = "document"
    rank: int = 0
    retrieval_method: str = "vector"
    vector_rank: int | None = None
    vector_score: float | None = None
    keyword_rank: int | None = None
    keyword_score: float | None = None
    fused_score: float | None = None
    rerank_score: float | None = None
    section: str = ""
    page: int | None = None
    char_range: tuple[int, int] | None = None
    content_hash: str = ""
    index_version: str = "legacy-v1"
    confidence: float | None = None
    quality_reason: str = ""
    provider: str | None = None
    tool_call_id: str | None = None
    as_of: str | None = None
    expires_at: str | None = None
    status: str = "ready"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Citation:
    """服务端生成的可核验证据引用。"""

    id: str
    chunk_id: str
    document_id: str
    source: dict[str, Any]
    quote: str
    locator: dict[str, Any] = field(default_factory=dict)
    retrieval: dict[str, Any] = field(default_factory=dict)
    index_version: str = "legacy-v1"
    evidence_type: EvidenceKind = "document"
    confidence: float = 0.0
    quality_reason: str = ""
    provider: str | None = None
    tool_call_id: str | None = None
    as_of: str | None = None
    expires_at: str | None = None
    status: str = "ready"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalTrace:
    """一次查询的路由、耗时、证据过滤和降级状态。"""

    route: str = "no_match"
    index_version: str = "legacy-v1"
    degraded: bool = False
    fallback_reason: str | None = None
    latency_ms: int = 0
    candidate_count: int = 0
    filtered_count: int = 0
    vector_count: int = 0
    keyword_count: int = 0
    route_candidates: list[str] = field(default_factory=list)
    chosen_route: str = "no_match"
    filter_reasons: list[str] = field(default_factory=list)
    manifest_id: str | None = None
    channels: dict[str, dict[str, Any]] = field(default_factory=dict)
    answer_citation_ids: list[str] = field(default_factory=list)
    citation_validation: str = "not_checked"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
