"""
RAG (Retrieval-Augmented Generation) service.
Migrated from msx_rag_project — integrates ChromaDB vector search
into the main MSX Assistant backend.
"""
import os
import json
import re
from typing import Optional, List, Dict, Tuple
from config import get_settings

settings = get_settings()

# ─── ChromaDB client (lazy init) ─────────────────────────────────
_chroma_client  = None
_chroma_collection = None

CHROMA_PATH       = os.environ.get("CHROMA_DB_PATH", "./msx_chroma_db")
CHROMA_COLLECTION = os.environ.get("CHROMA_COLLECTION", "msx_data")
EMBEDDING_MODEL   = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")


def get_chroma_collection():
    """Get or create ChromaDB collection (lazy init)."""
    global _chroma_client, _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        embedding_fn   = embedding_functions.OllamaEmbeddingFunction(
            url=f"{settings.localai_base_url.replace('/v1','')}/api/embeddings",
            model_name=EMBEDDING_MODEL,
        )
        _chroma_collection = _chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            embedding_function=embedding_fn,
        )
        count = _chroma_collection.count()
        print(f"✅ ChromaDB connected: {count} chunks in '{CHROMA_COLLECTION}'")
        return _chroma_collection
    except Exception as e:
        print(f"⚠️ ChromaDB unavailable: {e}")
        return None


def rag_search(query: str, top_k: int = 4) -> Tuple[Optional[str], List[str]]:
    """
    Search ChromaDB for relevant chunks.
    Returns (context_text, sources_list).
    """
    col = get_chroma_collection()
    if col is None:
        return None, []

    try:
        results = col.query(query_texts=[query], n_results=top_k)
        docs    = results.get("documents", [[]])[0]
        metas   = results.get("metadatas", [[]])[0]

        if not docs:
            return None, []

        context = "\n\n".join(docs)
        sources = list({m.get("url", "") for m in metas if m.get("url")})
        return context, sources

    except Exception as e:
        print(f"⚠️ RAG search error: {e}")
        return None, []


# ─── Keyword search fallback (from api.py) ────────────────────────

_msx_json_data: Optional[List[Dict]] = None

def load_msx_json() -> List[Dict]:
    """Load msx_data.json into memory (fallback search)."""
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


STOPWORDS = {
    "the","a","an","is","are","was","were","what","who","how",
    "when","where","tell","me","about","of","in","and","or",
    "for","to","do","did","does","give","list","get","find",
    "show","i","want","need","please","can","could","would",
    "ما","هو","هي","من","في","على","عن","هل","كيف","متى"
}

def _keywords(q: str) -> List[str]:
    return [
        w.strip("?.,!()\"'") for w in q.split()
        if len(w.strip("?.,!()\"'")) > 1
        and w.strip("?.,!()\"'").lower() not in STOPWORDS
    ]

def _get_matching_lines(content: str, keywords: List[str], window: int = 3) -> List[str]:
    lines   = content.split("\n")
    matched = set()
    for i, line in enumerate(lines):
        if any(kw.lower() in line.lower() for kw in keywords):
            for j in range(max(0, i-window), min(len(lines), i+window+1)):
                matched.add(j)
    result, prev = [], -2
    for i in sorted(matched):
        if i > prev + 1:
            result.append("---")
        if lines[i].strip():
            result.append(lines[i].strip())
        prev = i
    return result

def json_search(query: str, top_k: int = 3) -> Tuple[Optional[str], List[str]]:
    """Keyword-based search over msx_data.json."""
    docs  = load_msx_json()
    if not docs:
        return None, []
    keywords = _keywords(query)
    if not keywords:
        return None, []
    scored = []
    for doc in docs:
        content    = doc.get("content", "")
        individual = [content.lower().count(kw.lower()) for kw in keywords]
        all_found  = all(c > 0 for c in individual)
        score      = sum(individual) * (3 if all_found else 1)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: -x[0])
    top = [d for _, d in scored[:top_k]]
    if not top:
        return None, []
    parts   = []
    sources = []
    for doc in top:
        sources.append(doc["url"])
        lines = _get_matching_lines(doc["content"], keywords, window=3)
        parts.append(
            f"=== {doc['url']} ===\n"
            + "\n".join(lines)
            + f"\n\n{doc['content'][:2000]}"
        )
    return "\n\n".join(parts), sources


def search_rag(query: str, top_k: int = 4) -> Tuple[Optional[str], List[str], str]:
    """
    Main RAG search — tries ChromaDB first, falls back to JSON keyword search.
    Returns (context, sources, method).
    """
    # Try ChromaDB (semantic search)
    context, sources = rag_search(query, top_k)
    if context:
        return context, sources, "chromadb"

    # Fallback: keyword search over JSON
    context, sources = json_search(query, top_k)
    if context:
        return context, sources, "json_search"

    return None, [], "none"
