"""调用真实后端验证冻结的演示场景；不修改业务数据。"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def request_json(url: str, payload=None, timeout: float = 60) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def evaluate_scenario(scenario: dict, code: int, body: dict) -> list[str]:
    """检查真实回答是否满足冻结场景的最小业务契约。"""
    reasons = []
    if code != 200:
        return [f"http_status={code}"]

    retrieval = body.get("retrieval") or {}
    citations = body.get("citations") or []
    expected_routes = set(scenario.get("expected_routes") or [])
    route = retrieval.get("route")
    if expected_routes and route not in expected_routes:
        reasons.append(f"route={route}")

    citation_policy = scenario.get("citation")
    if citation_policy == "required" and not citations:
        reasons.append("citations_missing")
    elif citation_policy == "forbidden":
        if citations:
            reasons.append("citations_present")
        if retrieval.get("citation_validation") != scenario.get("citation_validation"):
            reasons.append(f"citation_validation={retrieval.get('citation_validation')}")
    elif citation_policy == "fresh_or_degraded":
        degraded = bool(retrieval.get("degraded"))
        if degraded and citations:
            reasons.append("degraded_citations_present")
        if not degraded and not citations:
            reasons.append("fresh_citations_missing")
    return reasons


def main() -> int:
    parser = argparse.ArgumentParser(description="真实后端演示 smoke")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--scenarios", default=str(ROOT / "evals" / "demo_scenarios.json"))
    parser.add_argument("--duration-seconds", type=int, default=0)
    parser.add_argument("--output")
    args = parser.parse_args()
    base = args.api_base_url.rstrip("/")
    status, readiness = request_json(f"{base}/api/readiness")
    report = {"readiness_http_status": status, "readiness": readiness, "scenarios": []}
    if status != 200 or readiness.get("status") != "ready":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    scenarios = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))["scenarios"]
    live_scenarios = [item for item in scenarios if not item.get("coverage")]
    deadline = time.monotonic() + args.duration_seconds if args.duration_seconds else None
    while True:
        for scenario in live_scenarios:
            started = time.monotonic()
            code, body = request_json(
                f"{base}/api/chat/text",
                {"query": scenario["query"], "interests": []},
            )
            retrieval = body.get("retrieval") or {}
            reasons = evaluate_scenario(scenario, code, body)
            report["scenarios"].append({
                "id": scenario["id"],
                "http_status": code,
                "latency_ms": round((time.monotonic() - started) * 1000, 3),
                "route": retrieval.get("route"),
                "citations": len(body.get("citations") or []),
                "citation_validation": retrieval.get("citation_validation"),
                "fallback_reason": retrieval.get("fallback_reason"),
                "passed": not reasons,
                "reasons": reasons,
            })
        if deadline is None or time.monotonic() >= deadline:
            break

    report["covered_by_contract_test"] = [
        item["id"] for item in scenarios if item.get("coverage") == "failure_contract"
    ]
    report["passed"] = all(item["passed"] for item in report["scenarios"])
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
