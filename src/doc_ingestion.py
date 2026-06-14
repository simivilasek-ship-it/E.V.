"""
JARVIS Document Ingestion — PDF, DOCX, TXT extraction for RAG.
Usage: from src.doc_ingestion import ingest_file, query_docs
"""
from __future__ import annotations
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DOCS_DIR = Path.home() / ".jarvis" / "docs"
_INDEX_FILE = _DOCS_DIR / "index.json"


def _extract_pdf(path: Path) -> str:
    """Extract text from PDF using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        return f"[pypdf not installed — run: pip install pypdf]"
    except Exception as e:
        return f"[PDF error: {e}]"


def _extract_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return f"[python-docx not installed — run: pip install python-docx]"
    except Exception as e:
        return f"[DOCX error: {e}]"


def _extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(path)
    elif ext in (".docx", ".doc"):
        return _extract_docx(path)
    elif ext in (".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".csv"):
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"[Read error: {e}]"
    return f"[Unsupported format: {ext}]"


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks for better retrieval."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('. ')
            last_newline = chunk.rfind('\n')
            break_at = max(last_period, last_newline)
            if break_at > chunk_size // 2:
                chunk = text[start:start + break_at + 1]
                end = start + break_at + 1
        chunks.append(chunk.strip())
        start = end - overlap
    return [c for c in chunks if c.strip()]


def _load_index() -> dict:
    if _INDEX_FILE.exists():
        try:
            return json.loads(_INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_index(idx: dict) -> None:
    _DOCS_DIR.mkdir(parents=True, exist_ok=True)
    _INDEX_FILE.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")


def ingest_file(path: str | Path) -> dict:
    """Ingest a file into the document store. Returns metadata dict."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return {"ok": False, "error": f"File not found: {p}"}

    text = _extract_text(p)
    if not text.strip():
        return {"ok": False, "error": "No text extracted"}

    # Content-based hash prevents duplicates when ingesting via temp paths
    doc_id = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]

    _DOCS_DIR.mkdir(parents=True, exist_ok=True)
    idx = _load_index()

    # Dedup: if content already indexed, update name/path but skip re-extraction
    if doc_id in idx:
        idx[doc_id]["path"] = str(p)
        idx[doc_id]["name"] = p.name
        _save_index(idx)
        existing = idx[doc_id]
        logger.info(f"Dedup: {p.name} already indexed as {doc_id}")
        return {
            "ok": True,
            "doc_id": doc_id,
            "name": p.name,
            "chars": existing.get("chars", 0),
            "chunks": existing.get("chunks", 1),
            "dedup": True,
        }

    # Split into overlapping chunks and persist each one
    chunks = _chunk_text(text)
    for i, chunk in enumerate(chunks):
        chunk_file = _DOCS_DIR / f"{doc_id}_chunk_{i}.txt"
        chunk_file.write_text(chunk, encoding="utf-8")

    idx[doc_id] = {
        "path": str(p),
        "name": p.name,
        "size": len(text),
        "chars": len(text),
        "chunks": len(chunks),
    }
    _save_index(idx)

    logger.info(f"Ingested {p.name} ({len(text)} chars, {len(chunks)} chunks) → {doc_id}")
    return {"ok": True, "doc_id": doc_id, "name": p.name, "chars": len(text), "chunks": len(chunks)}


def list_docs() -> list[dict]:
    """List all ingested documents."""
    idx = _load_index()
    return [{"id": k, **v} for k, v in idx.items()]


def _load_chunks(doc_id: str, meta: dict) -> list[str]:
    """Load all chunk texts for a document, falling back to single file."""
    chunk_count = meta.get("chunks", 0)
    chunks: list[str] = []

    if chunk_count and chunk_count > 0:
        for i in range(chunk_count):
            cf = _DOCS_DIR / f"{doc_id}_chunk_{i}.txt"
            if cf.exists():
                try:
                    chunks.append(cf.read_text(encoding="utf-8"))
                except Exception:
                    pass

    # Backward-compat: fall back to monolithic file
    if not chunks:
        legacy = _DOCS_DIR / f"{doc_id}.txt"
        if legacy.exists():
            try:
                chunks = [legacy.read_text(encoding="utf-8")]
            except Exception:
                pass

    return chunks


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def query_docs(query: str, top_k: int = 3, max_chars: int = 2000) -> str:
    """Keyword + optional semantic search over ingested docs. Returns relevant passages."""
    idx = _load_index()
    if not idx:
        return ""

    query_lower = query.lower()
    query_words = query_lower.split()

    # (score, doc_name, chunk_text) for all matching chunks
    results: list[tuple[float, str, str]] = []

    for doc_id, meta in idx.items():
        chunks = _load_chunks(doc_id, meta)
        doc_name = meta.get("name", doc_id)

        for chunk in chunks:
            score = sum(chunk.lower().count(w) for w in query_words)
            if score > 0:
                results.append((score, doc_name, chunk.strip()))

    if not results:
        return ""

    results.sort(key=lambda x: -x[0])

    # Semantic re-ranking via EmbeddingEngine when available
    try:
        from memory import EmbeddingEngine  # type: ignore
        _emb = EmbeddingEngine()
        if _emb.available:
            query_vec = _emb.embed(query)
            reranked: list[tuple[float, str, str]] = []
            for _kw_score, name, chunk in results:
                chunk_vec = _emb.embed(chunk)
                sem_score = _cosine_similarity(query_vec, chunk_vec)
                # Blend keyword rank + semantic score
                reranked.append((sem_score, name, chunk))
            reranked.sort(key=lambda x: -x[0])
            results = reranked
    except Exception:
        pass  # fall back to keyword ranking

    # Deduplicate near-identical passages (prefix overlap > 80%)
    seen: list[str] = []
    deduped: list[tuple[float, str, str]] = []
    for score, name, chunk in results:
        prefix = chunk[:100]
        if any(prefix in s or s in prefix for s in seen):
            continue
        seen.append(prefix)
        deduped.append((score, name, chunk))

    parts: list[str] = []
    total = 0
    for _score, name, chunk in deduped[:top_k]:
        if total + len(chunk) > max_chars:
            remaining = max_chars - total
            if remaining > 100:
                parts.append(f"[{name}]\n{chunk[:remaining].strip()}")
            break
        parts.append(f"[{name}]\n{chunk}")
        total += len(chunk)

    return "\n\n---\n\n".join(parts)


def delete_doc(doc_id: str) -> bool:
    idx = _load_index()
    if doc_id not in idx:
        return False

    meta = idx[doc_id]
    # Remove chunk files
    chunk_count = meta.get("chunks", 0)
    if chunk_count:
        for i in range(chunk_count):
            cf = _DOCS_DIR / f"{doc_id}_chunk_{i}.txt"
            if cf.exists():
                cf.unlink()
    # Remove legacy monolithic file if present
    legacy = _DOCS_DIR / f"{doc_id}.txt"
    if legacy.exists():
        legacy.unlink()

    del idx[doc_id]
    _save_index(idx)
    return True
