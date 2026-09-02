"""混合召回核心单元测试。"""
from app.core.rag import HybridRAGService
from app.core.retrieval_types import RAGResult


def result(content, chunk_id, method, rank, score):
    return RAGResult(
        content=content,
        source="doc.txt",
        score=score,
        chunk_id=chunk_id,
        retrieval_method=method,
        vector_rank=rank if method == "vector" else None,
        vector_score=score if method == "vector" else None,
        keyword_rank=rank if method == "keyword" else None,
        keyword_score=score if method == "keyword" else None,
    )


def test_rrf_deduplicates_and_is_stable():
    merged = HybridRAGService._merge(
        [result("同一证据", "a", "vector", 1, .8), result("向量证据", "b", "vector", 2, .7)],
        [result("同一证据", "a", "keyword", 1, 9), result("关键词证据", "c", "keyword", 2, 8)],
        final_k=5,
    )
    assert [item.chunk_id for item in merged] == ["a", "b", "c"]
    assert merged[0].vector_rank == 1
    assert merged[0].keyword_rank == 1
    assert merged[0].score > merged[1].score


def test_rrf_final_k_is_applied():
    merged = HybridRAGService._merge(
        [result(str(index), str(index), "vector", index, .5) for index in range(1, 5)],
        [],
        final_k=2,
    )
    assert len(merged) == 2
    assert [item.rank for item in merged] == [1, 2]


def test_single_route_keeps_actual_retrieval_method():
    vector = result("向量证据", "v", "vector", 1, .8)
    keyword = result("关键词证据", "k", "keyword", 1, 9)
    assert HybridRAGService._merge([vector], [], 5)[0].retrieval_method == "vector"
    assert HybridRAGService._merge([], [keyword], 5)[0].retrieval_method == "keyword"


def test_hybrid_prefers_non_empty_canonical_fields():
    vector = result("旧向量正文", "same", "vector", 1, .8)
    keyword = result("规范正文", "same", "keyword", 1, 9)
    keyword.document_id = "doc-1"
    keyword.content_hash = "hash-1"
    keyword.char_range = (2, 6)
    keyword.index_version = "hybrid-v1"
    merged = HybridRAGService._merge([vector], [keyword], 5)
    assert merged[0].retrieval_method == "hybrid"
    assert merged[0].content == "规范正文"
    assert merged[0].document_id == "doc-1"
    assert merged[0].char_range == (2, 6)
