"""运行可追溯的文档召回基线评测，只读 SQLite 和 Chroma。"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

# 支持从 backend/tools/evaluate_rag.py 直接运行。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import resolve_runtime_path, settings
from app.core.index_readiness import canonical_fingerprint
from app.core.index_runtime import get_active_index
from app.core.rag import HybridRAGService, RAG_AVAILABLE
from app.services.query_coordinator import build_citations

SUITE_VERSION = "rag-baseline-v2"
CANONICAL_MISSING_RE = re.compile(r"canonical_missing=(\d+)")
METRIC_KS = (5, 10)


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    """读取 JSONL 标注集，拒绝非对象记录和重复 case_id。"""
    cases = []
    seen = set()
    with Path(path).open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            text = line.strip()
            if not text:
                continue
            try:
                case = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"第 {line_number} 行不是有效 JSON: {exc}") from exc
            if not isinstance(case, dict):
                raise ValueError(f"第 {line_number} 行必须是 JSON 对象")
            case_id = str(case.get("case_id") or f"line-{line_number}")
            if case_id in seen:
                raise ValueError(f"重复 case_id: {case_id}")
            query = str(case.get("query") or "").strip()
            if not query:
                raise ValueError(f"第 {line_number} 行 query 不能为空")
            case["case_id"] = case_id
            case["query"] = query
            case["relevant_chunks"] = case.get("relevant_chunks") or []
            case["expected_document_ids"] = case.get("expected_document_ids") or []
            case["evaluation_type"] = str(
                case.get("evaluation_type")
                or ("production_refusal" if case.get("should_refuse") else "document_recall")
            )
            case["qrel_status"] = str(case.get("qrel_status") or "approved")
            seen.add(case_id)
            cases.append(case)
    return cases


def stable_chunk_key(document_sha256: str, chunk_sha256: str, chunk_index: int | None = None) -> str:
    """生成与随机 document/chunk ID 无关的评测键。"""
    key = f"{document_sha256}:{chunk_sha256}"
    return f"{key}:{chunk_index}" if chunk_index is not None else key


def _canonical_rows(sqlite_path: str | Path) -> dict[str, dict[str, Any]]:
    """读取 ready canonical chunks，评测过程不执行任何写操作。"""
    with sqlite3.connect(str(sqlite_path)) as connection:
        rows = connection.execute(
            "SELECT c.id, c.document_id, c.content, c.content_sha256, c.chunk_index, "
            "c.char_start, c.char_end, c.index_version, d.content_sha256 "
            "FROM chunks c JOIN documents d ON d.id = c.document_id "
            "WHERE COALESCE(c.status, 'ready') = 'ready' "
            "AND COALESCE(d.status, 'ready') = 'ready'"
        ).fetchall()
    return {
        str(row[0]): {
            "chunk_id": str(row[0]),
            "document_id": str(row[1] or ""),
            "content": str(row[2] or ""),
            "content_sha256": str(row[3] or ""),
            "chunk_index": row[4],
            "char_start": row[5],
            "char_end": row[6],
            "index_version": str(row[7] or "hybrid-v1"),
            "document_sha256": str(row[8] or ""),
        }
        for row in rows
    }


def resolve_relevant_chunk_ids(case: dict[str, Any], canonical: dict[str, dict[str, Any]]) -> set[str]:
    """把稳定 chunk 标注键映射为当前数据库中的 chunk ID。"""
    ids = set()
    by_key: dict[str, set[str]] = {}
    for chunk_id, row in canonical.items():
        key = stable_chunk_key(row["document_sha256"], row["content_sha256"])
        by_key.setdefault(key, set()).add(chunk_id)
        indexed_key = stable_chunk_key(
            row["document_sha256"], row["content_sha256"], row["chunk_index"]
        )
        by_key.setdefault(indexed_key, set()).add(chunk_id)

    for item in case.get("relevant_chunks", []):
        if isinstance(item, str):
            ids.update(by_key.get(item, set()))
            continue
        if not isinstance(item, dict):
            continue
        document_sha = str(item.get("document_sha256") or "")
        chunk_sha = str(item.get("chunk_sha256") or item.get("content_sha256") or "")
        if not document_sha or not chunk_sha:
            continue
        chunk_index = item.get("chunk_index")
        key = stable_chunk_key(document_sha, chunk_sha, chunk_index)
        matched = by_key.get(key, set())
        if not matched and chunk_index is not None:
            matched = by_key.get(stable_chunk_key(document_sha, chunk_sha), set())
        ids.update(matched)
    return ids


def resolve_relevant_document_ids(case: dict[str, Any], canonical: dict[str, dict[str, Any]]) -> set[str]:
    """解析人工批准的文档级 qrel，不把整份文档展开为全部 chunk。"""
    expected = {str(value) for value in case.get("expected_document_ids", []) if value}
    if not expected:
        return set()
    return {
        row["document_id"]
        for row in canonical.values()
        if row["document_id"] in expected or row["document_sha256"] in expected
    }


def percentile(values: Iterable[float], percentage: float) -> float:
    """使用线性插值计算稳定的 P50/P95。"""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return round(ordered[0], 3)
    position = (len(ordered) - 1) * percentage / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    value = ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    return round(value, 3)


def reciprocal_rank(returned_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, chunk_id in enumerate(returned_ids, 1):
        if chunk_id in relevant_ids:
            return 1 / rank
    return 0.0


def ndcg_at_k(returned_ids: list[str], relevant_ids: set[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0
    gains = [1 if chunk_id in relevant_ids else 0 for chunk_id in returned_ids[:k]]
    dcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))
    ideal_count = min(len(relevant_ids), k)
    ideal = sum(1 / math.log2(rank + 2) for rank in range(ideal_count))
    return dcg / ideal if ideal else 0.0


def validate_citations(citations, canonical: dict[str, dict[str, Any]]) -> tuple[int, int, int, int]:
    """返回 citation 总数、canonical 有效数、locator 总数、locator 有效数。"""
    canonical_total = canonical_valid = locator_total = locator_valid = 0
    for citation in citations:
        canonical_total += 1
        row = canonical.get(citation.chunk_id)
        canonical_quote = (row["content"] or "").strip() if row else ""
        if canonical_quote:
            canonical_quote = canonical_quote[:220].rstrip()
            if len((row["content"] or "").strip()) > 220:
                canonical_quote += "…"
        if row and citation.quote == canonical_quote:
            canonical_valid += 1
        locator = citation.locator or {}
        start, end = locator.get("char_start"), locator.get("char_end")
        if start is not None or end is not None:
            locator_total += 1
            if row and start == row["char_start"] and end == row["char_end"]:
                locator_valid += 1
    return canonical_total, canonical_valid, locator_total, locator_valid


def _first_rank(results, predicate) -> int | None:
    for item in results:
        if predicate(item):
            return item.rank
    return None


def _channel_rank(results, field: str, relevant_ids: set[str]) -> int | None:
    ranks = [getattr(item, field) for item in results if item.chunk_id in relevant_ids and getattr(item, field)]
    return min(ranks) if ranks else None


def _active_index_details(sqlite_path: str | Path, canonical: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """记录评测所用 active 索引和 canonical 指纹，保证结果可追溯。"""
    active = get_active_index(str(sqlite_path))
    manifest: dict[str, Any] = {}
    if active.get("manifest_id"):
        with sqlite3.connect(str(sqlite_path)) as connection:
            row = connection.execute(
                "SELECT id, version, vector_collection, fts_namespace, embedding_model, config_hash, content_hash "
                "FROM index_manifests WHERE id = ?",
                (active["manifest_id"],),
            ).fetchone()
        if row:
            manifest = {
                "manifest_id": str(row[0]),
                "index_version": str(row[1]),
                "vector_collection": str(row[2]),
                "fts_namespace": str(row[3]),
                "embedding_model": str(row[4]),
                "config_hash": str(row[5]),
                "manifest_fingerprint": str(row[6]),
            }
    rows = [
        SimpleNamespace(
            id=row["chunk_id"],
            document_id=row["document_id"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            char_start=row["char_start"],
            char_end=row["char_end"],
        )
        for row in canonical.values()
    ]
    return {
        "manifest_id": active.get("manifest_id"),
        "index_version": active.get("version"),
        "vector_collection": active.get("vector_collection"),
        "fts_namespace": active.get("fts_namespace"),
        "canonical_fingerprint": canonical_fingerprint(rows),
        **manifest,
    }


def _result_diagnostics(results, canonical: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """输出排序诊断，不输出任何证据正文。"""
    diagnostics = []
    for item in results:
        row = canonical.get(item.chunk_id, {})
        diagnostics.append({
            "rank": item.rank,
            "chunk_id": item.chunk_id,
            "document_id": item.document_id,
            "document_sha256": row.get("document_sha256", ""),
            "vector_rank": item.vector_rank,
            "keyword_rank": item.keyword_rank,
            "vector_score": item.vector_score,
            "keyword_score": item.keyword_score,
            "fused_score": item.fused_score,
        })
    return diagnostics


def evaluate(
    cases: list[dict[str, Any]],
    service,
    sqlite_path: str | Path,
    *,
    candidate_k: int = 30,
    final_k: int = 30,
    dataset_sha256: str = "",
) -> dict[str, Any]:
    """执行 document recall 基线并显式报告待复核 qrel。"""
    if candidate_k < max(METRIC_KS) or final_k < max(METRIC_KS):
        raise ValueError(f"candidate_k 和 final_k 必须至少为 {max(METRIC_KS)}")

    canonical = _canonical_rows(sqlite_path)
    route_counts = Counter()
    latencies = []
    returned_cases = []
    failures = []
    unresolved_qrels = []
    recall5 = []
    recall10 = []
    mrr = []
    ndcg = []
    document_recall5 = []
    document_recall10 = []
    citation_total = citation_valid = locator_total = locator_valid = 0
    missing_total = degraded_count = 0
    document_case_count = 0
    delegated_refusals = []

    for case in cases:
        evaluation_type = case.get("evaluation_type")
        if evaluation_type == "production_refusal":
            delegated_refusals.append({
                "case_id": case["case_id"],
                "production_suite_case_id": case.get("production_suite_case_id"),
                "expected_route": case.get("expected_route"),
                "expected_citation_validation": case.get("expected_citation_validation"),
            })
            continue
        if evaluation_type != "document_recall":
            unresolved_qrels.append({
                "case_id": case["case_id"],
                "reason": f"unsupported_evaluation_type:{evaluation_type}",
            })
            continue

        document_case_count += 1
        if case.get("qrel_status") != "approved":
            unresolved_qrels.append({
                "case_id": case["case_id"],
                "reason": case.get("unresolved_reason") or f"qrel_status:{case.get('qrel_status')}",
            })
            continue

        relevant_chunk_ids = resolve_relevant_chunk_ids(case, canonical)
        relevant_document_ids = resolve_relevant_document_ids(case, canonical)
        if not relevant_chunk_ids and not relevant_document_ids:
            unresolved_qrels.append({
                "case_id": case["case_id"],
                "reason": "approved_qrel_not_resolved",
            })
            continue

        started = time.perf_counter()
        trace = service.search_with_trace(case["query"], candidate_k=candidate_k, final_k=final_k)
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies.append(elapsed_ms)
        route_counts[trace.route] += 1
        degraded_count += int(trace.degraded)
        missing_match = CANONICAL_MISSING_RE.search(trace.fallback_reason or "")
        if missing_match:
            missing_total += int(missing_match.group(1))

        returned_ids = [item.chunk_id for item in trace.results]
        relevant5 = set(returned_ids[:5]) & relevant_chunk_ids
        relevant10 = set(returned_ids[:10]) & relevant_chunk_ids
        if relevant_chunk_ids:
            recall5.append(len(relevant5) / len(relevant_chunk_ids))
            recall10.append(len(relevant10) / len(relevant_chunk_ids))
            mrr.append(reciprocal_rank(returned_ids, relevant_chunk_ids))
            ndcg.append(ndcg_at_k(returned_ids, relevant_chunk_ids, 5))
            if not relevant5:
                failures.append({
                    "case_id": case["case_id"],
                    "reason": "relevant_chunk_not_in_top5",
                    "returned_chunk_ids": returned_ids,
                })
        if relevant_document_ids:
            returned_documents = [item.document_id for item in trace.results]
            document_recall5.append(len(set(returned_documents[:5]) & relevant_document_ids) / len(relevant_document_ids))
            document_recall10.append(len(set(returned_documents[:10]) & relevant_document_ids) / len(relevant_document_ids))

        returned_cases.append({
            "case_id": case["case_id"],
            "latency_ms": round(elapsed_ms, 3),
            "route": trace.route,
            "degraded": trace.degraded,
            "fallback_reason": trace.fallback_reason,
            "gold_chunk_count": len(relevant_chunk_ids),
            "gold_document_count": len(relevant_document_ids),
            "gold_rank": _first_rank(trace.results, lambda item: item.chunk_id in relevant_chunk_ids),
            "bge_gold_rank": _channel_rank(trace.results, "vector_rank", relevant_chunk_ids),
            "fts_gold_rank": _channel_rank(trace.results, "keyword_rank", relevant_chunk_ids),
            "returned": _result_diagnostics(trace.results, canonical),
        })

        citations = build_citations(trace.results)
        totals = validate_citations(citations, canonical)
        citation_total += totals[0]
        citation_valid += totals[1]
        locator_total += totals[2]
        locator_valid += totals[3]

    chunk_recall5 = round(sum(recall5) / len(recall5), 6) if recall5 else None
    chunk_recall10 = round(sum(recall10) / len(recall10), 6) if recall10 else None
    reproducibility = {
        "dataset_sha256": dataset_sha256,
        "candidate_k": candidate_k,
        "final_k": final_k,
        "metric_ks": list(METRIC_KS),
        "active_index": _active_index_details(sqlite_path, canonical),
    }
    return {
        "suite_version": SUITE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "index_version": reproducibility["active_index"]["index_version"],
        "query_count": len(cases),
        "document_recall_case_count": document_case_count,
        "scored_query_count": len(recall5),
        "unresolved_qrel_count": len(unresolved_qrels),
        "unresolved_qrels": unresolved_qrels,
        "production_refusal_cases": {
            "case_count": len(delegated_refusals),
            "delegated_to": "lingguide-demo-v1",
            "cases": delegated_refusals,
        },
        "route_counts": dict(route_counts),
        "chunk_recall_at_5": chunk_recall5,
        "chunk_recall_at_10": chunk_recall10,
        "document_recall_at_5": round(sum(document_recall5) / len(document_recall5), 6) if document_recall5 else None,
        "document_recall_at_10": round(sum(document_recall10) / len(document_recall10), 6) if document_recall10 else None,
        "recall_at_5": chunk_recall5,
        "recall_at_10": chunk_recall10,
        "mrr": round(sum(mrr) / len(mrr), 6) if mrr else None,
        "ndcg_at_5": round(sum(ndcg) / len(ndcg), 6) if ndcg else None,
        "citation_canonical_rate": round(citation_valid / citation_total, 6) if citation_total else None,
        "citation_locator_rate": round(locator_valid / locator_total, 6) if locator_total else None,
        "canonical_missing_total": missing_total,
        "degraded_rate": round(degraded_count / len(returned_cases), 6) if returned_cases else 0.0,
        "latency_ms_p50": percentile(latencies, 50),
        "latency_ms_p95": percentile(latencies, 95),
        "failures": failures,
        "cases": returned_cases,
        "reproducibility": reproducibility,
        "dependencies": {
            "rag_available": bool(RAG_AVAILABLE),
            "embedding_model": str(settings.embedding_model),
            "storage": "sqlite + embedded chroma",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读运行文档召回基线评测")
    parser.add_argument("--dataset", default=str(PROJECT_ROOT / "evals" / "rag_baseline.jsonl"))
    parser.add_argument("--sqlite", default=resolve_runtime_path(settings.sqlite_path))
    parser.add_argument("--chroma", default=resolve_runtime_path(settings.chroma_path))
    parser.add_argument("--output", help="将结果 JSON 写入指定文件")
    parser.add_argument("--candidate-k", type=int, default=30)
    parser.add_argument("--final-k", type=int, default=30)
    parser.add_argument("--thresholds", help="JSON 阈值文件，配合 --gate 使用")
    parser.add_argument("--gate", action="store_true", help="指标不达标时以非零状态退出")
    return parser.parse_args()


def check_thresholds(report: dict[str, Any], thresholds: dict[str, Any]) -> list[str]:
    """返回未达到的最小发布门槛。"""
    failures = []
    for key, minimum in thresholds.get("minimum", {}).items():
        actual = report.get(key)
        if actual is None or float(actual) < float(minimum):
            failures.append(f"{key}<{minimum} (actual={actual})")
    for key, maximum in thresholds.get("maximum", {}).items():
        actual = report.get(key)
        if actual is None or float(actual) > float(maximum):
            failures.append(f"{key}>{maximum} (actual={actual})")
    for key, expected in thresholds.get("equals", {}).items():
        actual = report.get(key)
        if actual != expected:
            failures.append(f"{key}!={expected} (actual={actual})")
    return failures


def main() -> int:
    args = parse_args()
    if args.candidate_k < max(METRIC_KS) or args.final_k < max(METRIC_KS):
        raise SystemExit(f"--candidate-k 和 --final-k 必须至少为 {max(METRIC_KS)}")
    if not Path(args.sqlite).is_file():
        raise SystemExit(f"SQLite 文件不存在: {args.sqlite}")
    if not Path(args.chroma).is_dir():
        raise SystemExit(f"Chroma 目录不存在；评测默认只读，不会自动创建: {args.chroma}")
    cases = load_cases(args.dataset)
    service = HybridRAGService(sqlite_path=args.sqlite, chroma_path=args.chroma)
    report = evaluate(
        cases,
        service,
        args.sqlite,
        candidate_k=args.candidate_k,
        final_k=args.final_k,
        dataset_sha256=_sha256(args.dataset),
    )
    gate_failures = []
    if args.thresholds:
        thresholds_path = Path(args.thresholds)
        thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
        gate_failures = check_thresholds(report, thresholds)
    if args.gate and report["unresolved_qrel_count"]:
        gate_failures.append(f"unresolved_qrel_count!=0 (actual={report['unresolved_qrel_count']})")
    if args.thresholds or args.gate:
        report["gate"] = {"passed": not gate_failures, "failures": gate_failures}
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 1 if args.gate and gate_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
