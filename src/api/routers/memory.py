"""Auto-migrated from dashboard.py — memory routes."""
from __future__ import annotations

import asyncio
import json
import time

import psutil

from src.api.deps import (
    HAS_LOGURU,
    __version__,
    get_scheduler,
    get_security_manager,
    logger,
    logger_module_available,
    start_time,
)
from src.api.paths import ROOT
from src.api.ws import (
    confirm_mgr,
    graph_clients,
    graph_mgr,
    ws_clients,
    ws_mgr,
)

if logger_module_available:
    pass  # imports satisfied above
else:
    def get_scheduler():  # type: ignore
        raise RuntimeError("scheduler unavailable")

    def get_security_manager():  # type: ignore
        raise RuntimeError("security unavailable")


def register(app):

    @app.get("/api/memory")
    async def memory_query(q: str = ""):
        """Dotaz do E.V. paměti."""
        try:
            from memory import JarvisMemory
            from config import CONFIG
            mem = JarvisMemory(CONFIG)
            results = mem.recall(q, top_k=5) if q else []
            stats   = mem.stats()
            return {"results": results, "stats": stats}
        except Exception as e:
            return {"results": [], "error": str(e)}

    @app.get("/api/memory/graph")
    async def memory_graph():
        """Vrátí paměť jako force-directed graf (nodes + links)."""
        try:
            from memory import JarvisMemory
            from config import CONFIG
            mem   = JarvisMemory(CONFIG)
            items = mem.recall("", top_k=60, min_importance=0.0)

            nodes, links = [], []
            seen_ids = set()

            for item in items:
                nid  = str(item["id"])
                text = item["content"][:60] + ("…" if len(item["content"]) > 60 else "")
                imp  = item.get("importance", 0.5)
                tags = item.get("tags", [])
                nodes.append({
                    "id": nid, "label": text,
                    "full": item["content"][:200],
                    "importance": round(imp, 2), "tags": tags,
                    "group": tags[0] if tags else "memory",
                    "ts": item.get("created_at", 0),
                })
                seen_ids.add(nid)

            # Hrany: 1) sdílený tag, 2) překrývající slova, 3) časová blízkost
            node_list = list(nodes)
            for i, a in enumerate(node_list):
                for b in node_list[i+1:]:
                    label = None
                    # 1. Sdílený tag
                    common_tags = set(a["tags"]) & set(b["tags"])
                    if common_tags:
                        label = list(common_tags)[0]
                    else:
                        # 2. Sdílená klíčová slova (3+ znaky, mimo stop-slova)
                        stop = {"the","and","for","that","this","jsou","bylo","není","nebo"}
                        wa = {w for w in a["full"].lower().split() if len(w) > 3 and w not in stop}
                        wb = {w for w in b["full"].lower().split() if len(w) > 3 and w not in stop}
                        common_words = wa & wb
                        if len(common_words) >= 2:
                            label = list(common_words)[0]
                        # 3. Časová blízkost (< 60 minut)
                        elif a["ts"] and b["ts"] and abs(a["ts"] - b["ts"]) < 3600:
                            label = "časově blízké"
                    if label:
                        links.append({"source": a["id"], "target": b["id"], "label": label})
                        if len(links) >= 120:
                            break
                if len(links) >= 120:
                    break

            # Integrate GraphStore (entities + relations) if available
            try:
                if getattr(mem, 'graph_store', None):
                    try:
                        gd = mem.graph_store.dump()
                        # merge graph nodes (prefix with 'g-' to avoid id collision)
                        for n in gd.get('nodes', []):
                            nid = 'g-' + str(n.get('id'))
                            if nid not in seen_ids:
                                nodes.append({
                                    'id': nid,
                                    'label': n.get('label') or n.get('name'),
                                    'full': n.get('label') or n.get('name'),
                                    'importance': n.get('importance', 0.5),
                                    'tags': [],
                                    'group': n.get('group', 'entity'),
                                    'ts': 0,
                                })
                                seen_ids.add(nid)
                        for l in gd.get('links', []):
                            links.append({'source': 'g-' + str(l.get('source')), 'target': 'g-' + str(l.get('target')), 'label': l.get('label')})
                    except Exception:
                        pass
            except Exception:
                pass

            # Limit s total_count
            total = len(nodes)
            result = {"nodes": nodes[:80], "links": links[:120], "total": total}
            try:
                from config import CONFIG
                if CONFIG.get('memory_graph_timeline', True):
                    # timeline: recent relation events (ts, subject, predicate, object)
                    timeline = []
                    for l in links:
                        if l.get('ts'):
                            timeline.append({
                                'ts': l.get('ts'),
                                'subject_id': l.get('source'),
                                'object_id': l.get('target'),
                                'predicate': l.get('label'),
                                'source': l.get('source_meta'),
                                'confidence': l.get('confidence'),
                            })
                    timeline.sort(key=lambda x: x['ts'], reverse=True)
                    result['timeline'] = timeline[:80]
            except Exception:
                pass
            return result
        except Exception as e:
            return {"nodes": [], "links": [], "error": str(e)}


