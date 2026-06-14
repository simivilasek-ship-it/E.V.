# Backward-compatibility shim — real module lives in src/doc_ingestion.py
from src.doc_ingestion import *  # noqa: F401, F403
from src.doc_ingestion import ingest_file, list_docs, query_docs, delete_doc  # noqa: F401
