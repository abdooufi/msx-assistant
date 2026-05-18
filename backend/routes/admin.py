from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import AdminStats, Conversation, UnansweredQuestion, FAQ, KnowledgeBase
from database import get_db
from auth import get_current_admin
from typing import Optional

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def get_stats(db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    total_conversations = (await db.execute(select(func.count()).select_from(Conversation))).scalar()
    unanswered_count    = (await db.execute(select(func.count()).select_from(UnansweredQuestion).where(UnansweredQuestion.status == "pending"))).scalar()
    faq_count           = (await db.execute(select(func.count()).select_from(FAQ))).scalar()
    knowledge_count     = (await db.execute(select(func.count()).select_from(KnowledgeBase))).scalar()

    convs = (await db.execute(select(Conversation))).scalars().all()
    total_messages = sum(len(c.messages or []) for c in convs)

    classification_breakdown = {}
    for conv in convs:
        for msg in (conv.messages or []):
            if msg.get("role") == "assistant" and msg.get("classification"):
                c = msg["classification"]
                classification_breakdown[c] = classification_breakdown.get(c, 0) + 1

    result = await db.execute(
        select(KnowledgeBase.category, func.count().label("count"))
        .group_by(KnowledgeBase.category)
        .order_by(func.count().desc()).limit(5)
    )
    top_categories = [{"category": r[0], "count": r[1]} for r in result.all()]

    return AdminStats(
        total_conversations=total_conversations,
        total_messages=total_messages,
        unanswered_count=unanswered_count,
        faq_count=faq_count,
        knowledge_count=knowledge_count,
        classification_breakdown=classification_breakdown,
        top_categories=top_categories,
    )


@router.get("/models")
async def get_models(_: str = Depends(get_current_admin)):
    from services.localai import get_available_models
    from config import get_settings
    s = get_settings()
    models = await get_available_models()
    return {
        "available_models": models,
        "configured": {
            "primary":  s.localai_model,
            "fallback": s.localai_model_fallback,
            "fast":     s.localai_model_fast,
            "analysis": s.localai_model_analysis,
        }
    }


# ─── Cache Management ─────────────────────────────────────────────

@router.get("/cache/stats")
async def get_cache_stats_endpoint(_: str = Depends(get_current_admin)):
    """Get Redis cache statistics."""
    from cache import get_cache_stats
    return await get_cache_stats()


@router.delete("/cache/{symbol}")
async def clear_symbol_cache(symbol: str, _: str = Depends(get_current_admin)):
    """Clear all cached data for a specific symbol."""
    from cache import invalidate_symbol
    count = await invalidate_symbol(symbol.upper())
    return {"symbol": symbol.upper(), "cleared": count, "message": f"Cleared {count} cache entries for {symbol.upper()}"}


@router.delete("/cache")
async def clear_all_cache(_: str = Depends(get_current_admin)):
    """Clear ALL MSX cache entries."""
    from cache import cache_delete_pattern
    count = await cache_delete_pattern("msx:*")
    return {"cleared": count, "message": f"Cleared {count} total cache entries"}
