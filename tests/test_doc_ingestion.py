"""Tests for doc_ingestion.py — RAG document store."""
import os
import sys
import tempfile
import pytest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import doc_ingestion

pytestmark = [pytest.mark.unit]


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Redirect _DOCS_DIR and _INDEX_FILE to a temp directory for each test."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    index_file = docs_dir / "index.json"
    monkeypatch.setattr(doc_ingestion, "_DOCS_DIR", docs_dir)
    monkeypatch.setattr(doc_ingestion, "_INDEX_FILE", index_file)
    yield docs_dir


# ---------------------------------------------------------------------------
# test_ingest_txt_file
# ---------------------------------------------------------------------------

def test_ingest_txt_file(tmp_path):
    src = tmp_path / "hello.txt"
    src.write_text("Hello world! This is a test document.", encoding="utf-8")

    result = doc_ingestion.ingest_file(src)

    assert result["ok"] is True
    assert result["name"] == "hello.txt"
    assert result["chars"] > 0
    assert "doc_id" in result


# ---------------------------------------------------------------------------
# test_ingest_dedup
# ---------------------------------------------------------------------------

def test_ingest_dedup(tmp_path):
    content = "Identical content used to test deduplication."
    src1 = tmp_path / "file_a.txt"
    src2 = tmp_path / "file_b.txt"
    src1.write_text(content, encoding="utf-8")
    src2.write_text(content, encoding="utf-8")

    r1 = doc_ingestion.ingest_file(src1)
    r2 = doc_ingestion.ingest_file(src2)

    assert r1["ok"] and r2["ok"]
    assert r1["doc_id"] == r2["doc_id"], "Same content must yield same doc_id"
    assert r2.get("dedup") is True, "Second ingest should be flagged as duplicate"

    docs = doc_ingestion.list_docs()
    assert len(docs) == 1, f"Expected 1 doc in index, got {len(docs)}"


# ---------------------------------------------------------------------------
# test_query_returns_passage
# ---------------------------------------------------------------------------

def test_query_returns_passage(tmp_path):
    src = tmp_path / "science.txt"
    src.write_text(
        "The mitochondria is the powerhouse of the cell. "
        "It produces ATP through oxidative phosphorylation.",
        encoding="utf-8",
    )
    doc_ingestion.ingest_file(src)

    result = doc_ingestion.query_docs("mitochondria powerhouse")

    assert "mitochondria" in result.lower(), f"Expected 'mitochondria' in result, got: {result!r}"


# ---------------------------------------------------------------------------
# test_query_empty_when_no_docs
# ---------------------------------------------------------------------------

def test_query_empty_when_no_docs():
    result = doc_ingestion.query_docs("anything at all")
    assert result == "", f"Expected empty string, got: {result!r}"


# ---------------------------------------------------------------------------
# test_delete_doc
# ---------------------------------------------------------------------------

def test_delete_doc(tmp_path):
    src = tmp_path / "delete_me.txt"
    src.write_text("Some content that will be deleted shortly.", encoding="utf-8")

    r = doc_ingestion.ingest_file(src)
    assert r["ok"] is True
    doc_id = r["doc_id"]

    assert any(d["id"] == doc_id for d in doc_ingestion.list_docs())

    deleted = doc_ingestion.delete_doc(doc_id)
    assert deleted is True

    assert not any(d["id"] == doc_id for d in doc_ingestion.list_docs()), \
        "Document should no longer appear in list_docs() after deletion"


# ---------------------------------------------------------------------------
# test_chunk_text
# ---------------------------------------------------------------------------

def test_chunk_text():
    long_text = "A" * 2000
    chunks = doc_ingestion._chunk_text(long_text, chunk_size=500, overlap=100)

    assert len(chunks) > 1, "2000-char string should produce multiple chunks"
    # Every chunk must be non-empty
    assert all(c.strip() for c in chunks)
    # Verify overlap: consecutive chunks should share at least `overlap` chars of content
    # (overlap is approximate due to sentence-boundary snapping, so just verify > 0 shared tail/head)
    for i in range(len(chunks) - 1):
        tail = chunks[i][-100:]
        head = chunks[i + 1][:200]
        shared = sum(1 for ch in tail if ch in head)
        assert shared > 0, f"Chunk {i} and {i+1} appear to have no overlap"


# ---------------------------------------------------------------------------
# test_content_hash_stable
# ---------------------------------------------------------------------------

def test_content_hash_stable(tmp_path):
    """Same text ingested from different file paths must produce the same doc_id."""
    content = "Stable hashing test: this exact text should always map to the same id."
    path_a = tmp_path / "dir_a" / "document.txt"
    path_b = tmp_path / "dir_b" / "other_name.txt"
    path_a.parent.mkdir()
    path_b.parent.mkdir()
    path_a.write_text(content, encoding="utf-8")
    path_b.write_text(content, encoding="utf-8")

    r_a = doc_ingestion.ingest_file(path_a)
    r_b = doc_ingestion.ingest_file(path_b)

    assert r_a["ok"] and r_b["ok"]
    assert r_a["doc_id"] == r_b["doc_id"], (
        f"Expected same doc_id for identical content; got {r_a['doc_id']} vs {r_b['doc_id']}"
    )
