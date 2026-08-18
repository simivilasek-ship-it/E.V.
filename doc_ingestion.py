# Backward-compatibility shim — real module lives in src/doc_ingestion.py
from src.doc_ingestion import *  # noqa: F401, F403
from src.doc_ingestion import (  # noqa: F401
    ingest_file,
    list_docs,
    query_docs,
    delete_doc,
    _DOCS_DIR,
    _INDEX_FILE,
    _chunk_text,
)
