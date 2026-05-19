"""
Unified retrieval service.
Priority order:
1. FAQ table (PostgreSQL) — exact matches
2. Knowledge Base table (PostgreSQL) — scraped MSX pages
3. Qdrant RAG — semantic vector search (embedding via Ollama)
4. JSON keyword search — fallback
"""
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
import re


def _score(text: str, query: str) -> float:
    words    = set(re.findall(r'\w+', query.lower()))
    doc_w    = set(re.findall(r'\w+', text.lower()))
    if not words: return 0.0
    return len(words & doc_w) / len(words)


async def search_faqs(db: AsyncSession, query: str, limit: int = 3) -> list:
    from models import FAQ
    result = await db.execute(
        select(FAQ).where(
            FAQ.is_active == True,
            or_(FAQ.question.ilike(f"%{query}%"), FAQ.answer.ilike(f"%{query}%"))
        ).limit(limit * 3)
    )
    faqs   = result.scalars().all()
    scored = sorted(faqs, key=lambda f: _score(f.question + " " + f.answer, query), reverse=True)
    return scored[:limit]


async def search_knowledge_base(db: AsyncSession, query: str, limit: int = 3) -> list:
    from models import KnowledgeBase
    result = await db.execute(
        select(KnowledgeBase).where(
            or_(KnowledgeBase.title.ilike(f"%{query}%"), KnowledgeBase.content.ilike(f"%{query}%"))
        ).limit(limit * 3)
    )
    docs   = result.scalars().all()
    scored = sorted(docs, key=lambda d: _score(d.title + " " + d.content, query), reverse=True)
    return scored[:limit]


async def build_context(db: AsyncSession, query: str) -> Tuple[Optional[str], str, List[str]]:
    """
    Full retrieval pipeline with 4 fallback layers.
    Returns (context_text, source_type, references).
    """
    # 1. FAQ — highest priority
    faqs = await search_faqs(db, query)
    if faqs:
        parts = ["📋 Relevant FAQ Entries:"]
        refs  = []
        for faq in faqs:
            parts.append(f"Q: {faq.question}\nA: {faq.answer}")
            refs.append(faq.question)
        return "\n\n".join(parts), "faq", refs

    # 2. Knowledge Base (PostgreSQL — scraped MSX pages)
    kb_docs = await search_knowledge_base(db, query)
    if kb_docs:
        parts = ["📚 Relevant Knowledge Base Articles:"]
        refs  = []
        for doc in kb_docs:
            parts.append(f"Title: {doc.title}\nSource: {doc.source or ''}\n{doc.content[:800]}")
            refs.append(doc.title)
        return "\n\n".join(parts), "knowledge_base", refs

    # 3. Qdrant RAG / JSON keyword search
    try:
        from services.rag import search_rag
        context, sources, method = await search_rag(query)
        if context:
            refs  = sources[:3]
            label = "Qdrant" if method == "qdrant" else "MSX Data"
            return f"📖 {label} Search Results:\n\n{context}", "knowledge_base", refs
    except Exception as e:
        print(f"⚠️ RAG search error: {e}")

    return None, "ai_general", []
