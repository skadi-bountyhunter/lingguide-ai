"""统一查询编排：FAQ、结构化景点和混合文档召回。"""
from __future__ import annotations

import asyncio
import hashlib
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from app.core.rag import rag_service
from app.config import settings
from app.core.retrieval_types import Citation, RAGResult, RetrievalTrace
from app.core.tools.amap_tools import (
    SCENIC_ALIASES,
    SCENIC_CONTEXT_TERMS,
    amap_weather_evidence,
    is_foreign_lingshan,
)
from app.core.locales import canonicalize_query, normalize_locale
from app.core.llm import _clean_response
from app.services.structured_retriever import structured_retriever
from app.core.timing import elapsed_ms, started

# 文档证据必须同时具备可核验身份和最小相关性，不能仅因 canonical 身份完整进入 LLM。
DEFAULT_EVIDENCE_CONFIDENCE = 0.10
_CITATION_PATTERN = re.compile(r"(?:\[|【)\s*C(\d+)\s*(?:\]|】)")
_ROUTE_TERMS = ("路线", "规划", "游览顺序", "怎么走", "几个景点", "一日游", "半日游", "半天游", "全天游")
# 这类请求明确要求未收录、未公开或预测性数据，不能把无关景区资料当作证据回答。
_UNSUPPORTED_REQUEST_PATTERNS = (
    "资料库中没有", "资料库里没有", "未公开", "手机号码", "实时客流", "精确客流", "预测明年",
    "不存在景点",
)


class QueryResult:
    """供各聊天入口消费的统一查询结果。"""

    def __init__(
        self,
        results=None,
        route="no_match",
        degraded=False,
        fallback_reason=None,
        trace_id=None,
        *,
        filter_reasons: list[str] | None = None,
        route_candidates: list[str] | None = None,
    ):
        self.results: list[RAGResult] = results or []
        self.route = route
        self.degraded = degraded
        self.fallback_reason = fallback_reason
        self.trace_id = trace_id or f"trace_{uuid.uuid4().hex}"
        self.filter_reasons = filter_reasons or []
        self.route_candidates = route_candidates or ([route] if route != "no_match" else [])
        self.citations = build_citations(self.results)
        self.trace = RetrievalTrace(
            route=route,
            chosen_route=route,
            route_candidates=self.route_candidates,
            degraded=degraded,
            fallback_reason=fallback_reason,
            candidate_count=len(self.results),
            filtered_count=0,
            filter_reasons=self.filter_reasons,
            vector_count=sum(1 for item in self.results if item.vector_rank),
            keyword_count=sum(1 for item in self.results if item.keyword_rank),
        )

    @property
    def sources(self) -> list[str]:
        seen = set()
        sources = []
        for citation in self.citations:
            filename = citation.source.get("filename") or citation.source.get("title") or "未知来源"
            if filename not in seen:
                seen.add(filename)
                sources.append(filename)
        return sources

    @property
    def has_evidence(self) -> bool:
        return bool(self.citations)

    def as_dict(self) -> dict[str, Any]:
        return {
            "citations": [item.to_dict() for item in self.citations],
            "retrieval": self.trace.to_dict(),
            "trace_id": self.trace_id,
        }

    def clear_evidence(self, validation: str) -> None:
        """拒答时移除与最终回复语义冲突的候选证据。"""
        self.results = []
        self.citations = []
        self.trace.answer_citation_ids = []
        self.trace.citation_validation = validation

    def mark_generation_failure(self, reason: str, validation: str = "generation_failed") -> None:
        """将生成失败统一为无证据的保守回复状态。"""
        reasons = [item for item in (self.trace.fallback_reason or "").split(";") if item]
        if reason not in reasons:
            reasons.append(reason)
        self.trace.fallback_reason = ";".join(reasons)
        self.fallback_reason = self.trace.fallback_reason
        self.trace.degraded = True
        self.degraded = True
        self.clear_evidence(validation)


def _faq_candidates(query: str) -> list[tuple[dict[str, Any], int]]:
    """返回按置信度排序的 FAQ 候选，不在此处决定是否短路。"""
    from app.api.knowledge import FAQ_LIST, _normalize_faq_term

    text = _normalize_faq_term(query)
    if not text or any(_normalize_faq_term(term) in text for term in _ROUTE_TERMS):
        return []
    candidates = []
    for faq in FAQ_LIST:
        question = _normalize_faq_term(faq.get("question", ""))
        exact = [_normalize_faq_term(item) for item in faq.get("exact_questions", [])]
        if text == question or text in exact:
            candidates.append((faq, 1000 + len(question)))
            continue
        entities = [item for item in faq.get("entities", []) if item]
        intents = [item for item in faq.get("intent_keywords", []) if item]
        entity_hits = [item for item in entities if _normalize_faq_term(item) in text]
        intent_hits = [item for item in intents if _normalize_faq_term(item) in text]
        if entity_hits and intent_hits:
            candidates.append((faq, 100 + max(map(len, entity_hits)) + max(map(len, intent_hits))))
    return sorted(candidates, key=lambda item: item[1], reverse=True)


def match_faq(query: str) -> dict[str, Any] | None:
    """匹配高置信 FAQ；所有聊天入口共用这条规则。"""
    from app.api.knowledge import _normalize_faq_term

    candidates = _faq_candidates(query)
    if not candidates:
        return None
    best = candidates[0][1]
    tied = [item for item in candidates if item[1] == best]
    if len(tied) > 1 and len({_normalize_faq_term(item[0].get("intent")) for item in tied}) > 1:
        return None
    return candidates[0][0]


def faq_to_query_result(faq: dict[str, Any], trace_id: str | None = None) -> QueryResult:
    """将 FAQ 快路径转换为统一的可引用 QueryResult。"""
    answer = _clean_response(faq.get("answer", ""))
    faq_id = str(faq.get("id", "legacy"))
    item = RAGResult(
        content=answer,
        source="FAQ 精确匹配",
        score=1.0,
        chunk_id=f"faq:{faq_id}",
        document_id=f"faq:{faq_id}",
        source_type="faq",
        retrieval_method="faq",
        index_version="faq-v1",
        confidence=1.0,
        quality_reason="exact_or_entity_intent_match",
        status="ready",
    )
    result = QueryResult([item], route="faq", trace_id=trace_id)
    result.trace.candidate_count = 1
    result.trace.citation_validation = "valid"
    result.trace.answer_citation_ids = ["C1"]
    return result


def weather_to_query_result(evidence: Mapping[str, Any], trace_id: str | None = None) -> QueryResult:
    """把天气工具结果转换为统一的可过期证据。"""
    status = str(evidence.get("status") or "error")
    metadata = dict(evidence.get("metadata") or {})
    reason = str(evidence.get("fallback_reason") or metadata.get("reason") or "") or None
    result = QueryResult(
        route="weather",
        trace_id=trace_id,
        degraded=status != "ready",
        fallback_reason=reason,
    )
    if status == "ready" and evidence.get("content"):
        source = evidence.get("source") or {}
        item = RAGResult(
            content=str(evidence["content"]),
            source=str(source.get("title") or "天气服务"),
            score=float(evidence.get("confidence") or 0.0),
            chunk_id=str(evidence.get("id") or ""),
            document_id=f"weather:{evidence.get('provider') or 'unknown'}",
            source_type="weather",
            retrieval_method="weather",
            confidence=float(evidence.get("confidence") or 0.0),
            quality_reason=str(evidence.get("quality_reason") or "weather_tool"),
            provider=evidence.get("provider"),
            tool_call_id=evidence.get("tool_call_id"),
            as_of=evidence.get("as_of"),
            expires_at=evidence.get("expires_at"),
            status=status,
            index_version="weather-live",
            metadata=metadata,
        )
        accepted, reasons = filter_evidence([item], threshold=0.0)
        result.results = accepted
        result.filter_reasons = reasons
        result.citations = build_citations(accepted)
    result.trace.chosen_route = "weather"
    result.trace.route_candidates = ["weather", "document"]
    result.trace.candidate_count = len(result.results)
    result.trace.index_version = "weather-live"
    result.trace.channels["weather"] = {
        "status": status,
        "provider": evidence.get("provider", "amap"),
        "place": (evidence.get("source") or {}).get("title"),
        "tool_call_id": evidence.get("tool_call_id"),
        "as_of": evidence.get("as_of"),
        "expires_at": evidence.get("expires_at"),
        "reason": reason,
        "provider_code": metadata.get("provider_code"),
        "stage": metadata.get("stage"),
    }
    return result


def _result_confidence(result: RAGResult) -> float:
    """计算可解释的文档证据置信度，不改变旧 score 语义。"""
    if result.confidence is not None:
        return max(0.0, min(1.0, float(result.confidence)))
    fused = float(result.fused_score or 0.0)
    vector = float(result.vector_score or 0.0)
    keyword = float(result.keyword_score or 0.0)
    # RRF 用于排序，向量和关键词分数用于相关性判断；canonical 身份只在
    # filter_evidence 中校验，不能作为相关性加分。
    confidence = min(1.0, fused * 3.0 + max(0.0, vector) * 0.35 + max(0.0, keyword) * 0.05)
    return round(confidence, 6)


def filter_evidence(results: list[RAGResult], *, threshold: float = DEFAULT_EVIDENCE_CONFIDENCE) -> tuple[list[RAGResult], list[str]]:
    """过滤不可核验或明显过弱的证据，并返回可审计的原因。"""
    accepted: list[RAGResult] = []
    reasons: list[str] = []
    for result in results:
        confidence = _result_confidence(result)
        result.confidence = confidence
        if not result.content.strip():
            reasons.append(f"{result.chunk_id or 'unknown'}:empty_content")
            continue
        if not result.chunk_id or not result.document_id:
            reasons.append(f"{result.chunk_id or 'unknown'}:missing_canonical_id")
            continue
        if result.status not in {"ready", "active", ""}:
            reasons.append(f"{result.chunk_id}:status_{result.status}")
            continue
        if result.expires_at:
            try:
                expires_at = datetime.fromisoformat(result.expires_at.replace("Z", "+00:00"))
                if expires_at <= datetime.now(timezone.utc):
                    reasons.append(f"{result.chunk_id}:expired")
                    continue
            except ValueError:
                reasons.append(f"{result.chunk_id}:invalid_expiry")
                continue
        if confidence < threshold:
            reasons.append(f"{result.chunk_id}:confidence_{confidence:.4f}")
            continue
        result.quality_reason = result.quality_reason or "canonical_and_relevant"
        accepted.append(result)
    return accepted, reasons


def extract_citation_ids(text: str) -> list[str]:
    """提取回答中的 Citation ID，兼容中英文方括号。"""
    seen: set[str] = set()
    ids: list[str] = []
    for value in _CITATION_PATTERN.findall(text or ""):
        citation_id = f"C{int(value)}"
        if citation_id not in seen:
            seen.add(citation_id)
            ids.append(citation_id)
    return ids


def validate_answer_citations(text: str, citations: list[Citation]) -> tuple[list[str], list[str]]:
    """返回有效和未知引用；未知引用不得被当作可信引用。"""
    valid_ids = {citation.id for citation in citations}
    found = extract_citation_ids(text)
    return [item for item in found if item in valid_ids], [item for item in found if item not in valid_ids]


def build_citations(results: list[RAGResult]) -> list[Citation]:
    """从最终证据生成引用，引用内容始终来自实际召回结果。"""
    citations = []
    for index, result in enumerate(results, 1):
        quote = (result.content or "").strip()
        if len(quote) > 220:
            quote = quote[:220].rstrip() + "…"
        citations.append(Citation(
            id=f"C{index}",
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            source={
                "title": result.source,
                "filename": result.source,
                "type": result.source_type,
            },
            quote=quote,
            locator={
                "section": result.section,
                "page": result.page,
                "char_start": result.char_range[0] if result.char_range else None,
                "char_end": result.char_range[1] if result.char_range else None,
            },
            retrieval={
                "route": result.retrieval_method,
                "vector_rank": result.vector_rank,
                "keyword_rank": result.keyword_rank,
                "vector_score": result.vector_score,
                "keyword_score": result.keyword_score,
                "fused_score": result.fused_score,
                "confidence": result.confidence,
            },
            index_version=result.index_version,
            evidence_type=result.source_type if result.source_type in {"faq", "spot", "route", "document", "weather", "tool"} else "document",
            confidence=float(result.confidence or 0.0),
            quality_reason=result.quality_reason,
            provider=result.provider,
            tool_call_id=result.tool_call_id,
            as_of=result.as_of,
            expires_at=result.expires_at,
            status=result.status or "ready",
        ))
    return citations


class QueryCoordinator:
    """所有问答入口共用的检索协调器。"""

    @staticmethod
    def _is_weather_query(query: str) -> bool:
        return any(term in (query or "") for term in ("天气", "气温", "温度", "下雨", "带伞", "穿什么", "风力"))

    @staticmethod
    def _weather_location(query: str) -> tuple[str, str | None]:
        """保守抽取天气地点；景区泛称统一落到配置的无锡灵山。"""
        text = (query or "").strip()
        compact = text.replace(" ", "")
        # 明确的外地同名地点不能被“灵山”子串误判为本项目景区。
        if not is_foreign_lingshan(compact) and any(alias in compact for alias in SCENIC_ALIASES):
            return settings.weather_default_city, settings.weather_default_scope

        weather_terms = "天气|气温|温度|下雨|带伞|穿什么|风力"
        match = re.search(rf"([一-鿿]{{2,18}})(?:的)?(?:{weather_terms})", text)
        if not match:
            return settings.weather_default_city, settings.weather_default_scope

        candidate = match.group(1).strip()
        candidate = re.sub(r"^(?:请问|今天|明天|后天|现在|当前|此刻|去|到)+", "", candidate)
        suffixes = (
            "会不会", "要不要", "不适合", "今天", "明天", "后天", "现在", "当前", "此刻", "近日",
            "适合", "需要", "是否", "可以", "会", "要",
        )
        changed = True
        while candidate and changed:
            changed = False
            candidate = candidate.rstrip("的").strip()
            for suffix in suffixes:
                if candidate.endswith(suffix):
                    candidate = candidate[:-len(suffix)].rstrip("的").strip()
                    changed = True
                    break

        generic = set(SCENIC_CONTEXT_TERMS) | {"景区内", "这里景区", "景区这里"}
        if (
            not candidate
            or candidate in generic
            or any(separator in candidate for separator in ("和", "、", "以及"))
        ):
            return settings.weather_default_city, settings.weather_default_scope
        return candidate, None

    @staticmethod
    def _faq_covers_named_spots(
        query: str,
        faq: Mapping[str, Any],
        structured_results: list[RAGResult],
    ) -> bool:
        """泛化 FAQ 不得替代点名景点或多景点的讲解。"""
        from app.api.knowledge import _normalize_faq_term

        text = _normalize_faq_term(query)
        spot_names = [
            _normalize_faq_term(item.source)
            for item in structured_results
            if item.source_type == "spot" and _normalize_faq_term(item.source) in text
        ]
        named_spots = list(dict.fromkeys(spot_names))
        if not named_spots:
            return True
        faq_entities = {
            _normalize_faq_term(item)
            for item in faq.get("entities", [])
            if item
        }
        return len(named_spots) == 1 and any(
            named_spots[0] in entity or entity in named_spots[0]
            for entity in faq_entities
        )

    @staticmethod
    def _merge_channels(
        structured_results: list[RAGResult],
        document_results: list[RAGResult],
        final_k: int,
    ) -> tuple[list[RAGResult], dict[str, dict[str, Any]]]:
        """按稳定 evidence ID 合并结构化、向量和关键词通道。"""
        merged: dict[str, RAGResult] = {}
        channels: dict[str, dict[str, Any]] = {
            "structured": {"status": "ok", "count": len(structured_results)},
            "document": {"status": "ok", "count": len(document_results)},
        }
        for channel, items in (("structured", structured_results), ("document", document_results)):
            for rank, item in enumerate(items, 1):
                key = item.chunk_id or item.document_id or hashlib.sha256(item.content.encode("utf-8")).hexdigest()
                current = merged.get(key)
                if current is None:
                    current = item
                    current.fused_score = 0.0
                    merged[key] = current
                else:
                    current.fused_score = current.fused_score or 0.0
                    if item.content_hash and not current.content_hash:
                        current.content_hash = item.content_hash
                    if item.document_id and not current.document_id:
                        current.document_id = item.document_id
                    current.retrieval_method = "hybrid"
                current.fused_score += 1.0 / (60 + rank)
                if channel == "structured":
                    current.metadata = {**current.metadata, "structured_rank": rank}
                else:
                    current.metadata = {**current.metadata, "document_rank": rank}
        ordered = sorted(
            merged.values(),
            key=lambda item: (-(item.fused_score or 0.0), item.chunk_id),
        )
        for rank, item in enumerate(ordered[:final_k], 1):
            item.rank = rank
            item.score = round(item.fused_score or item.score, 6)
        return ordered[:final_k], channels

    async def retrieve_async(
        self,
        query: str,
        *,
        top_k: int = 5,
        locale: str = "zh-CN",
        trace_id: str | None = None,
        confidence_threshold: float = DEFAULT_EVIDENCE_CONFIDENCE,
    ) -> QueryResult:
        """按 FAQ、天气或结构化+FTS+BGE 三路通道路由。"""
        locale = normalize_locale(locale)
        query = canonicalize_query(query, locale)
        started_at = started()
        skipped = {
            "faq": {"status": "skipped", "latency_ms": 0, "count": 0},
            "structured": {"status": "skipped", "latency_ms": 0, "count": 0},
            "fts": {"status": "skipped", "latency_ms": 0, "count": 0, "fallback_used": False},
            "bge": {"status": "skipped", "latency_ms": 0, "count": 0},
            "weather": {"status": "skipped", "latency_ms": 0, "count": 0},
        }
        if any(pattern in (query or "") for pattern in _UNSUPPORTED_REQUEST_PATTERNS):
            result = QueryResult(route="no_match", trace_id=trace_id, fallback_reason="unsupported_or_unavailable_request")
            result.trace.citation_validation = "no_evidence"
            result.trace.channels = {**skipped, "policy": {"status": "refused", "reason": "unsupported_or_unavailable_request"}}
            result.trace.latency_ms = elapsed_ms(started_at)
            return result

        faq_started = started()
        faq = match_faq(query)
        faq_channel = {"status": "hit" if faq else "miss", "latency_ms": elapsed_ms(faq_started), "count": int(bool(faq))}
        structured_results: list[RAGResult] | None = None
        structured_channel = skipped["structured"]
        if faq:
            structured_started = started()
            structured_results = await asyncio.to_thread(structured_retriever.search, query, top_k=30)
            structured_channel = {
                "status": "ok" if structured_results else "empty",
                "latency_ms": elapsed_ms(structured_started),
                "count": len(structured_results),
            }
            if self._faq_covers_named_spots(query, faq, structured_results):
                result = faq_to_query_result(faq, trace_id)
                result.trace.channels = {**skipped, "faq": faq_channel, "structured": structured_channel, "llm": {"status": "skipped", "latency_ms": 0, "reason": "faq_short_circuit"}}
                result.trace.latency_ms = elapsed_ms(started_at)
                return result

        if self._is_weather_query(query):
            city, scope = self._weather_location(query)
            weather_started = started()
            try:
                evidence = await asyncio.wait_for(
                    amap_weather_evidence(city, scope),
                    timeout=settings.weather_timeout_seconds,
                )
            except asyncio.TimeoutError:
                evidence = {
                    "status": "error",
                    "provider": "amap",
                    "source": {"title": city, "type": "weather"},
                    "fallback_reason": "weather_deadline_exceeded",
                    "metadata": {"reason": "weather_deadline_exceeded"},
                }
            result = weather_to_query_result(evidence, trace_id)
            metadata = evidence.get("metadata") or {}
            result.trace.channels = {
                **skipped,
                "faq": faq_channel,
                "structured": structured_channel,
                "weather": {
                    **result.trace.channels.get("weather", {}),
                    "latency_ms": int(metadata.get("latency_ms", elapsed_ms(weather_started))),
                    "cache_hit": bool(metadata.get("cache_hit", False)),
                    "count": len(result.results),
                },
            }
            result.trace.latency_ms = elapsed_ms(started_at)
            return result

        try:
            result = await asyncio.wait_for(
                self._retrieve_channels_async(
                    query,
                    top_k=top_k,
                    trace_id=trace_id,
                    confidence_threshold=confidence_threshold,
                    structured_results=structured_results,
                    structured_channel=structured_channel,
                ),
                timeout=settings.retrieval_timeout_seconds,
            )
            result.trace.channels["faq"] = faq_channel
            result.trace.channels["weather"] = skipped["weather"]
            result.trace.latency_ms = elapsed_ms(started_at)
            return result
        except asyncio.TimeoutError:
            result = QueryResult(route="no_match", degraded=True, trace_id=trace_id, fallback_reason="retrieval_timeout")
            result.trace.degraded = True
            result.trace.fallback_reason = "retrieval_timeout"
            result.trace.citation_validation = "no_evidence"
            result.trace.channels = {
                **skipped,
                "faq": faq_channel,
                "structured": {**structured_channel, "status": "timeout" if structured_results is None else structured_channel["status"]},
                "fts": {"status": "timeout", "latency_ms": settings.retrieval_timeout_seconds * 1000, "count": 0, "fallback_used": False},
                "bge": {"status": "timeout", "latency_ms": settings.retrieval_timeout_seconds * 1000, "count": 0},
            }
            result.trace.latency_ms = elapsed_ms(started_at)
            return result

    async def _retrieve_channels_async(
        self,
        query: str,
        *,
        top_k: int,
        trace_id: str | None,
        confidence_threshold: float,
        structured_results: list[RAGResult] | None = None,
        structured_channel: dict[str, Any] | None = None,
    ) -> QueryResult:
        started_at = started()
        structured_started = started()
        structured_task = None if structured_results is not None else asyncio.to_thread(structured_retriever.search, query, top_k=30)
        document_task = asyncio.to_thread(rag_service.search_with_trace, query, final_k=30)
        if structured_task is None:
            document_outcome = await document_task
            structured_outcome = structured_results
        else:
            structured_outcome, document_outcome = await asyncio.gather(
                structured_task,
                document_task,
                return_exceptions=True,
            )
        if isinstance(structured_outcome, Exception):
            structured_results = []
            current_structured_channel = {
                "status": "failed",
                "latency_ms": elapsed_ms(structured_started),
                "count": 0,
                "reason": type(structured_outcome).__name__,
            }
        else:
            structured_results = structured_outcome or []
            current_structured_channel = structured_channel or {
                "status": "ok" if structured_results else "empty",
                "latency_ms": elapsed_ms(structured_started),
                "count": len(structured_results),
            }
        if isinstance(document_outcome, Exception):
            from types import SimpleNamespace
            search = SimpleNamespace(
                results=[], route="no_match", degraded=True,
                fallback_reason=f"document:{type(document_outcome).__name__}",
                vector_count=0, keyword_count=0,
                index_version="legacy-v1", manifest_id=None,
                channels={
                    "bge": {"status": "failed", "latency_ms": elapsed_ms(started_at), "count": 0, "reason": type(document_outcome).__name__},
                    "fts": {"status": "failed", "latency_ms": elapsed_ms(started_at), "count": 0, "fallback_used": False, "reason": type(document_outcome).__name__},
                },
            )
        else:
            search = document_outcome
        return self._build_result(
            structured_results,
            search,
            query=query,
            top_k=top_k,
            trace_id=trace_id,
            confidence_threshold=confidence_threshold,
            started=started_at,
            structured_channel=current_structured_channel,
        )

    def _build_result(
        self,
        structured_results: list[RAGResult],
        search,
        *,
        query: str,
        top_k: int,
        trace_id: str | None,
        confidence_threshold: float,
        started: float | None = None,
        structured_channel: dict[str, Any] | None = None,
    ) -> QueryResult:
        merged, channels = self._merge_channels(structured_results, search.results, top_k)
        channels["structured"] = structured_channel or {
            "status": "ok" if structured_results else "empty",
            "latency_ms": 0,
            "count": len(structured_results),
        }
        channels.update(getattr(search, "channels", {}) or {})
        if search.degraded and not search.results:
            channels["document"] = {
                "status": "failed",
                "count": 0,
                "reason": search.fallback_reason,
            }
        filtered, filter_reasons = filter_evidence(merged, threshold=confidence_threshold)
        active_routes = []
        if structured_results:
            active_routes.append("structured")
        if search.route != "no_match":
            active_routes.append(search.route)
        route = "hybrid" if len(active_routes) > 1 else (active_routes[0] if active_routes else "no_match")
        result = QueryResult(
            results=filtered,
            route=route if filtered else "no_match",
            degraded=search.degraded,
            fallback_reason=search.fallback_reason,
            trace_id=trace_id,
            filter_reasons=filter_reasons,
            route_candidates=active_routes,
        )
        result.trace.vector_count = search.vector_count
        result.trace.keyword_count = search.keyword_count
        result.trace.candidate_count = len(merged)
        result.trace.filtered_count = len(merged) - len(filtered)
        result.trace.latency_ms = int((time.perf_counter() - (started or time.perf_counter())) * 1000)
        result.trace.index_version = search.index_version
        result.trace.manifest_id = search.manifest_id
        for item in result.results:
            item.index_version = search.index_version
        result.citations = build_citations(result.results)
        result.trace.channels = channels
        if result.trace.filtered_count and not filtered:
            result.degraded = True
            result.trace.degraded = True
            result.trace.fallback_reason = ";".join(filter_reasons)
        return result

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        trace_id: str | None = None,
        confidence_threshold: float = DEFAULT_EVIDENCE_CONFIDENCE,
    ) -> QueryResult:
        """同步兼容入口；异步 API 使用并行通道。"""
        started = time.perf_counter()
        structured_results = structured_retriever.search(query, top_k=30)
        search = rag_service.search_with_trace(query, final_k=30)
        return self._build_result(
            structured_results,
            search,
            query=query,
            top_k=top_k,
            trace_id=trace_id,
            confidence_threshold=confidence_threshold,
            started=started,
        )


query_coordinator = QueryCoordinator()
