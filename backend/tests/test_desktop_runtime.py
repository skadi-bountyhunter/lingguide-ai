"""Windows 便携版运行契约测试。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.config import Settings
from app.main import _lite_readiness


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_desktop_settings_resolve_all_writes_to_data_root(tmp_path):
    resources = tmp_path / "resources"
    data = tmp_path / "LingGuideData"
    config = Settings(
        runtime_mode="desktop",
        resource_root=str(resources),
        data_root=str(data),
        rag_mode="lite",
    )
    assert config.app_debug is False
    assert config.sqlite_path == str(data / "lingguide.db")
    assert config.upload_dir == str(data / "uploads")
    assert config.chroma_path == str(data / "chroma")
    assert config.faq_path == str(data / "faqs.json")
    assert config.log_path == str(data / "logs" / "lingguide.log")


def test_lite_mode_does_not_import_vector_dependencies():
    script = (
        "import sys; import app.core.rag as rag; "
        "assert rag.RAG_AVAILABLE is False; "
        "assert 'chromadb' not in sys.modules; "
        "assert 'sentence_transformers' not in sys.modules"
    )
    environment = {**os.environ, "RAG_MODE": "lite"}
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_release_seed_is_clean_and_lite(tmp_path):
    output = tmp_path / "seed"
    result = subprocess.run(
        [
            sys.executable,
            str(BACKEND_ROOT / "tools" / "build_release_seed.py"),
            "--output-dir",
            str(output.resolve()),
        ],
        cwd=BACKEND_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(result.stdout.strip().splitlines()[-1])
    assert manifest["rag_mode"] == "lite"
    assert manifest["counts"]["spots"] == 22
    assert manifest["counts"]["routes"] == 5
    assert manifest["counts"]["faqs"] > 0
    assert manifest["counts"]["chunks"] == manifest["counts"]["faqs"]
    assert manifest["counts"]["chunk_fts"] == manifest["counts"]["chunks"]
    assert {item.name for item in output.iterdir()} == {
        "lingguide.db",
        "faqs.json",
        "manifest.json",
    }
    checks, details = _lite_readiness(str(output / "lingguide.db"))
    assert all(checks.values())
    assert details["faq_count"] > 0
