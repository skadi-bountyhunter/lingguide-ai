"""按生产问答链路评测冻结的竞赛演示集。"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.answer_orchestrator import NO_EVIDENCE_REPLY, generate_answer
from app.services.query_coordinator import QueryCoordinator
from tools.evaluate_rag import check_thresholds, load_cases, percentile


async def evaluate_demo(
    cases: list[dict[str, Any]],
    coordinator: QueryCoordinator,
    answer_fn: Callable[..., Awaitable[str]] = generate_answer,
) -> dict[str, Any]:
    """执行 FAQ、天气、结构化和文档的生产回答链路评测。"""
    latencies: list[float] = []
    case_reports: list[dict[str, Any]] = []
    route_ok = grounded_ok = refusal_ok = faq_ok = 0
    route_total = grounded_total = refusal_total = faq_total = 0
    citation_total = citation_valid = locator_total = locator_valid = 0
    canonical_missing_total = 0
    repeated: dict[str, list[tuple[str, tuple[str, ...], bool]]] = defaultdict(list)

    for case in cases:
        started = time.perf_counter()
        result = await coordinator.retrieve_async(case["query"], top_k=5)
        if result.route == "faq" and result.results:
            reply = result.results[0].content
        else:
            reply = await answer_fn(case["query"], result)
        elapsed = (time.perf_counter() - started) * 1000
        latencies.append(elapsed)

        expected_routes = set(case.get("expected_routes") or [])
        route_passed = not expected_routes or result.route in expected_routes
        route_total += 1
        route_ok += int(route_passed)

        should_refuse = bool(case.get("should_refuse"))
        citations = result.citations
        if should_refuse:
            refusal_total += 1
            refusal_passed = reply == NO_EVIDENCE_REPLY and not citations
            refusal_ok += int(refusal_passed)
            grounded_passed = refusal_passed
        else:
            required_terms = [str(item) for item in case.get("required_terms") or []]
            terms_passed = all(term in reply for term in required_terms)
            citation_required = bool(case.get("citation_required"))
            grounded_passed = terms_passed and (not citation_required or bool(citations))
            grounded_total += 1
            grounded_ok += int(grounded_passed)
            refusal_passed = None

        if case.get("category") == "faq":
            faq_total += 1
            faq_ok += int(result.route == "faq" and grounded_passed)

        for citation in citations:
            citation_total += 1
            valid = bool(citation.chunk_id and citation.document_id and citation.quote)
            citation_valid += int(valid)
            locator = citation.locator or {}
            if citation.evidence_type == "document":
                locator_total += 1
                locator_valid += int(
                    locator.get("char_start") is not None
                    and locator.get("char_end") is not None
                )
        canonical_missing_total += sum(
            int(reason.rsplit("=", 1)[1])
            for reason in (result.trace.fallback_reason or "").split(";")
            if "canonical_missing=" in reason and reason.rsplit("=", 1)[1].isdigit()
        )

        repeat_group = case.get("repeat_group")
        if repeat_group:
            repeated[str(repeat_group)].append((
                result.route,
                tuple(item.id for item in citations),
                reply == NO_EVIDENCE_REPLY,
            ))
        case_reports.append({
            "case_id": case["case_id"],
            "category": case.get("category", ""),
            "route": result.route,
            "route_passed": route_passed,
            "grounded_passed": grounded_passed,
            "refusal_passed": refusal_passed,
            "reply": reply,
            "citation_ids": [item.id for item in citations],
            "citation_validation": result.trace.citation_validation,
            "fallback_reason": result.trace.fallback_reason,
            "manifest_id": result.trace.manifest_id,
            "index_version": result.trace.index_version,
            "latency_ms": round(elapsed, 3),
        })

    repeat_total = len(repeated)
    repeat_ok = sum(1 for values in repeated.values() if len(set(values)) == 1)
    return {
        "suite_version": "lingguide-demo-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "query_count": len(cases),
        "route_accuracy": round(route_ok / route_total, 6) if route_total else None,
        "grounded_answer_accuracy": round(grounded_ok / grounded_total, 6) if grounded_total else None,
        "refusal_accuracy": round(refusal_ok / refusal_total, 6) if refusal_total else None,
        "faq_accuracy": round(faq_ok / faq_total, 6) if faq_total else None,
        "repeat_stability": round(repeat_ok / repeat_total, 6) if repeat_total else None,
        "citation_canonical_rate": round(citation_valid / citation_total, 6) if citation_total else None,
        "citation_locator_rate": round(locator_valid / locator_total, 6) if locator_total else None,
        "canonical_missing_total": canonical_missing_total,
        "latency_ms_p50": percentile(latencies, 50),
        "latency_ms_p95": percentile(latencies, 95),
        "cases": case_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="运行冻结演示集的最终回答评测")
    parser.add_argument("--dataset", default=str(ROOT / "evals" / "demo_eval_v1.jsonl"))
    parser.add_argument("--thresholds", default=str(ROOT / "evals" / "demo_thresholds.json"))
    parser.add_argument("--output")
    parser.add_argument("--gate", action="store_true")
    args = parser.parse_args()

    report = asyncio.run(evaluate_demo(load_cases(args.dataset), QueryCoordinator()))
    thresholds = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
    failures = check_thresholds(report, thresholds)
    report["gate"] = {"passed": not failures, "failures": failures}
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 1 if args.gate and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
