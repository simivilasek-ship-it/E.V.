"""
JARVIS Document Ingestion — PDF, DOCX, TXT extraction for RAG.
Usage: from doc_ingestion import ingest_file, query_docs
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

    doc_id = hashlib.sha256(str(p).encode()).hexdigest()[:16]
    chunk_file = _DOCS_DIR / f"{doc_id}.txt"
    _DOCS_DIR.mkdir(parents=True, exist_ok=True)
    chunk_file.write_text(text, encoding="utf-8")

    idx = _load_index()
    idx[doc_id] = {
        "path": str(p),
        "name": p.name,
        "size": len(text),
        "chars": len(text),
    }
    _save_index(idx)

    logger.info(f"Ingested {p.name} ({len(text)} chars) → {doc_id}")
    return {"ok": True, "doc_id": doc_id, "name": p.name, "chars": len(text)}


def list_docs() -> list[dict]:
    """List all ingested documents."""
    idx = _load_index()
    return [{"id": k, **v} for k, v in idx.items()]


def query_docs(query: str, top_k: int = 3, max_chars: int = 2000) -> str:
    """Simple keyword search over ingested docs. Returns relevant passages."""
    idx = _load_index()
    if not idx:
        return ""

    query_lower = query.lower()
    results: list[tuple[float, str, str]] = []

    for doc_id, meta in idx.items():
        chunk_file = _DOCS_DIR / f"{doc_id}.txt"
        if not chunk_file.exists():
            continue
        try:
            text = chunk_file.read_text(encoding="utf-8")
        except Exception:
            continue

        # Score: count query word occurrences
        words = query_lower.split()
        score = sum(text.lower().count(w) for w in words)
        if score > 0:
            # Find best passage (window around first match)
            idx_pos = text.lower().find(words[0]) if words else 0
            start = max(0, idx_pos - 200)
            end = min(len(text), idx_pos + 800)
            passage = text[start:end].strip()
            results.append((score, meta["name"], passage))

    if not results:
        return ""

    results.sort(key=lambda x: -x[0])
    parts = []
    total = 0
    for score, name, passage in results[:top_k]:
        if total + len(passage) > max_chars:
            break
        parts.append(f"[{name}]\n{passage}")
        total += len(passage)

    return "\n\n---\n\n".join(parts)


def delete_doc(doc_id: str) -> bool:
    idx = _load_index()
    if doc_id not in idx:
        return False
    chunk_file = _DOCS_DIR / f"{doc_id}.txt"
    if chunk_file.exists():
        chunk_file.unlink()
    del idx[doc_id]
    _save_index(idx)
    return True
