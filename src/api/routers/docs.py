"""Document ingestion and RAG endpoints."""
from __future__ import annotations

from fastapi import UploadFile, File
import tempfile
from pathlib import Path


def register(app):
    @app.post("/api/docs/upload")
    async def upload_doc(file: UploadFile = File(...)):
        """Upload and ingest a document (PDF, DOCX, TXT, MD, etc.)"""
        try:
            from doc_ingestion import ingest_file
            suffix = Path(file.filename or "upload.txt").suffix
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name
            result = ingest_file(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)
            if result["ok"]:
                result["original_name"] = file.filename
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.get("/api/docs")
    async def list_docs():
        """List all ingested documents."""
        try:
            from doc_ingestion import list_docs
            return {"docs": list_docs()}
        except Exception as e:
            return {"docs": [], "error": str(e)}

    @app.delete("/api/docs/{doc_id}")
    async def delete_doc(doc_id: str):
        try:
            from doc_ingestion import delete_doc
            ok = delete_doc(doc_id)
            return {"ok": ok}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @app.get("/api/docs/query")
    async def query_docs(q: str, top_k: int = 3):
        """Search ingested documents."""
        try:
            from doc_ingestion import query_docs
            result = query_docs(q, top_k=top_k)
            return {"result": result, "ok": bool(result)}
        except Exception as e:
            return {"result": "", "ok": False, "error": str(e)}
