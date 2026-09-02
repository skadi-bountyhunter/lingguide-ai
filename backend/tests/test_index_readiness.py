"""active RAG 索引严格就绪检查。"""
from types import SimpleNamespace

import pytest

from app.core.index_readiness import CHUNKING_CONFIG_HASH, assess_active_index, canonical_fingerprint


@pytest.fixture
def readiness_state():
    rows = [
        SimpleNamespace(
            id="chunk-1",
            document_id="doc-1",
            chunk_index=0,
            content="灵山大佛位于无锡",
            char_start=0,
            char_end=8,
        ),
        SimpleNamespace(
            id="chunk-2",
            document_id="doc-1",
            chunk_index=1,
            content="景区开放时间为八点",
            char_start=8,
            char_end=17,
        ),
    ]
    active = {
        "manifest_id": "manifest-1",
        "version": "shadow-1",
        "vector_collection": "lingguide_knowledge__shadow_1",
        "fts_namespace": "chunk_fts__shadow_1",
    }
    manifest = SimpleNamespace(
        id="manifest-1",
        version="shadow-1",
        state="active",
        vector_collection=active["vector_collection"],
        fts_namespace=active["fts_namespace"],
        embedding_model="BAAI/bge-large-zh-v1.5",
        config_hash=CHUNKING_CONFIG_HASH,
        content_hash=canonical_fingerprint(rows),
    )
    return rows, active, manifest


def test_active_index_readiness_accepts_matching_namespaces_and_ids(readiness_state):
    rows, active, manifest = readiness_state

    report = assess_active_index(
        manifest,
        active,
        rows,
        fts_available=True,
        fts_count=2,
        vector_ids=["chunk-1", "chunk-2"],
        expected_embedding_model="BAAI/bge-large-zh-v1.5",
        expected_config_hash=CHUNKING_CONFIG_HASH,
    )

    assert all(report["checks"].values())
    assert report["details"]["canonical_count"] == 2
    assert report["details"]["vector_ids_match"] is True


@pytest.mark.parametrize(
    ("change", "expected_check"),
    [
        ("manifest", "manifest"),
        ("fts", "fts"),
        ("ids", "ids"),
        ("fingerprint", "fingerprint"),
        ("config", "config"),
    ],
)
def test_active_index_readiness_rejects_each_mismatch(readiness_state, change, expected_check):
    rows, active, manifest = readiness_state
    fts_available = True
    fts_count = 2
    vector_ids = ["chunk-1", "chunk-2"]
    expected_embedding_model = "BAAI/bge-large-zh-v1.5"
    expected_config_hash = CHUNKING_CONFIG_HASH

    if change == "manifest":
        manifest = None
    elif change == "fts":
        fts_available = False
    elif change == "ids":
        vector_ids = ["chunk-1", "orphan"]
    elif change == "fingerprint":
        manifest.content_hash = "changed"
    elif change == "config":
        expected_config_hash = "different"

    report = assess_active_index(
        manifest,
        active,
        rows,
        fts_available=fts_available,
        fts_count=fts_count,
        vector_ids=vector_ids,
        expected_embedding_model=expected_embedding_model,
        expected_config_hash=expected_config_hash,
    )

    assert report["checks"][expected_check] is False
    assert not all(report["checks"].values())
