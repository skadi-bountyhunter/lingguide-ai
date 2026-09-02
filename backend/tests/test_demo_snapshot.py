"""冻结演示快照的只读校验测试。"""
import hashlib
import json
from pathlib import Path


def test_demo_manifest_references_forty_reviewed_cases():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "evals" / "demo_manifest.json").read_text(encoding="utf-8"))
    evaluation = manifest["evaluation"]
    dataset = root / evaluation["path"]
    content = dataset.read_bytes()
    cases = [
        json.loads(line)
        for line in content.decode("utf-8").splitlines()
        if line.strip()
    ]

    assert hashlib.sha256(content).hexdigest() == evaluation["sha256"]
    assert len(cases) == evaluation["case_count"] == 40
    assert all(case["review_status"] == "user_approved_for_demo" for case in cases)
    assert sum(case.get("should_refuse") is True for case in cases) >= 5
    assert {"faq", "weather", "route", "refusal"} <= {case["category"] for case in cases}
