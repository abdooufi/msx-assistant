"""
RAG pipeline using Qdrant for vector search.

Flow:
  User Question
      → Create Embedding  (Ollama /api/embeddings)
      → Search Qdrant     (nearest-vector lookup)
      → Get Relevant Data (payload text + URLs)
      → Send Context to Ollama
      → AI Answer
"""
import os
import json
import httpx
from typing import Optional, List, Dict, Tuple
from config import get_settings

settings = get_settings()

QDRANT_URL        = os.environ.get("QDRANT_URL",        settings.qdrant_url)
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", settings.qdrant_collection)
EMBEDDING_MODEL   = os.environ.get("EMBEDDING_MODEL",   settings.embedding_model)
EMBEDDING_URL     = settings.localai_base_url.replace("/v1", "") + "/api/embeddings"

_qdrant_client = None


def _get_qdrant():
    """Lazy-init Qdrant client; returns None if unavailable."""
    global _qdrant_client
    if _qdrant_client is not None:
        return _qdrant_client
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=QDRANT_URL, timeout=10)
        existing = {c.name for c in client.get_collections().collections}
        if QDRANT_COLLECTION in existing:
            count = client.count(QDRANT_COLLECTION).count
            print(f"✅ Qdrant connected: {count} vectors in '{QDRANT_COLLECTION}'")
        else:
            print(f"⚠️  Qdrant: collection '{QDRANT_COLLECTION}' not found — run load_qdrant.py first")
        _qdrant_client = client
        return client
    except Exception as e:
        print(f"⚠️  Qdrant unavailable: {e}")
        return None


async def _embed(text: str) -> Optional[List[float]]:
    """Step 1 — create embedding vector via Ollama."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                EMBEDDING_URL,
                json={"model": EMBEDDING_MODEL, "prompt": text},
            )
            r.raise_for_status()
            return r.json().get("embedding")
    except Exception as e:
        print(f"⚠️  Embedding error: {e}")
        return None


async def qdrant_search(query: str, top_k: int = 4) -> Tuple[Optional[str], List[str]]:
    """
    Steps 1-3 of the pipeline:
      1. Create embedding for the query
      2. Search Qdrant for the nearest vectors
      3. Return (context_text, source_urls)
    """
    client = _get_qdrant()
    if client is None:
        return None, []

    # Step 1 — embed
    vector = await _embed(query)
    if not vector:
        return None, []

    # Step 2 — search Qdrant
    try:
        hits = client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
            score_threshold=0.3,
        )
    except Exception as e:
        print(f"⚠️  Qdrant search error: {e}")
        return None, []

    if not hits:
        return None, []

    # Step 3 — get relevant data
    texts   = [h.payload.get("text", "") for h in hits if h.payload.get("text")]
    sources = list({h.payload.get("url", "") for h in hits if h.payload.get("url")})
    context = "\n\n".join(texts)
    return context or None, sources


# ─── Keyword search fallback ──────────────────────────────────────

_msx_json_data: Optional[List[Dict]] = None

def _load_msx_json() -> List[Dict]:
    global _msx_json_data
    if _msx_json_data is not None:
        return _msx_json_data
    for path in ["msx_data.json", "./msx_data.json", "../msx_data.json"]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                _msx_json_data = json.load(f)
            print(f"✅ Loaded msx_data.json: {len(_msx_json_data)} pages")
            return _msx_json_data
    _msx_json_data = []
    return []


_STOPWORDS = {
    "the","a","an","is","are","was","were","what","who","how",
    "when","where","tell","me","about","of","in","and","or",
    "for","to","do","did","does","give","list","get","find",
    "show","i","want","need","please","can","could","would",
    "ما","هو","هي","من","في","على","عن","هل","كيف","متى",
}

def _keywords(q: str) -> List[str]:
    return [
        w.strip("?.,!()\"'") for w in q.split()
        if len(w.strip("?.,!()\"'")) > 1
        and w.strip("?.,!()\"'").lower() not in _STOPWORDS
    ]

def _matching_lines(content: str, keywords: List[str], window: int = 3) -> List[str]:
    lines, matched = content.split("\n"), set()
    for i, line in enumerate(lines):
        if any(kw.lower() in line.lower() for kw in keywords):
            for j in range(max(0, i - window), min(len(lines), i + window + 1)):
                matched.add(j)
    result, prev = [], -2
    for i in sorted(matched):
        if i > prev + 1:
            result.append("---")
        if lines[i].strip():
            result.append(lines[i].strip())
        prev = i
    return result

def _json_search(query: str, top_k: int = 3) -> Tuple[Optional[str], List[str]]:
    docs, keywords = _load_msx_json(), _keywords(query)
    if not docs or not keywords:
        return None, []
    scored = []
    for doc in docs:
        content = doc.get("content", "")
        counts  = [content.lower().count(kw.lower()) for kw in keywords]
        score   = sum(counts) * (3 if all(c > 0 for c in counts) else 1)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: -x[0])
    top = [d for _, d in scored[:top_k]]
    if not top:
        return None, []
    parts, sources = [], []
    for doc in top:
        sources.append(doc["url"])
        lines = _matching_lines(doc["content"], keywords)
        parts.append(f"=== {doc['url']} ===\n" + "\n".join(lines) + f"\n\n{doc['content'][:2000]}")
    return "\n\n".join(parts), sources


# ─── Main entry point ────────────────────────────────────────────

async def search_rag(query: str, top_k: int = 4) -> Tuple[Optional[str], List[str], str]:
    """
    Main RAG search — Qdrant first, keyword fallback.
    Returns (context, sources, method).
    """
    context, sources = await qdrant_search(query, top_k)
    if context:
        return context, sources, "qdrant"

    context, sources = _json_search(query, top_k)
    if context:
        return context, sources, "json_search"

    return None, [], "none"
