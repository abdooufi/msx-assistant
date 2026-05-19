from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from models import AdminStats, Conversation, UnansweredQuestion, FAQ, KnowledgeBase, SystemSetting, AIProviderConfig
from database import get_db
from auth import get_current_admin
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def get_stats(db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    total_conversations = (await db.execute(select(func.count()).select_from(Conversation))).scalar()
    unanswered_count    = (await db.execute(select(func.count()).select_from(UnansweredQuestion).where(UnansweredQuestion.status == "pending"))).scalar()
    faq_count           = (await db.execute(select(func.count()).select_from(FAQ))).scalar()
    knowledge_count     = (await db.execute(select(func.count()).select_from(KnowledgeBase))).scalar()

    msg_count_row = await db.execute(
        text("SELECT COALESCE(SUM(jsonb_array_length(COALESCE(messages, '[]')::jsonb)), 0) FROM conversations")
    )
    total_messages = int(msg_count_row.scalar() or 0)

    convs = (await db.execute(select(Conversation))).scalars().all()
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


# ─── AI Provider Settings ─────────────────────────────────────────

_PROVIDER_KEYS = ["ai_provider", "deepseek_api_key", "deepseek_model", "deepseek_base_url"]


@router.get("/ai-settings")
async def get_ai_settings(db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    rows = (await db.execute(select(SystemSetting).where(SystemSetting.key.in_(_PROVIDER_KEYS)))).scalars().all()
    kv   = {r.key: r.value for r in rows}
    return {
        "provider":          kv.get("ai_provider",       "ollama"),
        "deepseek_api_key":  kv.get("deepseek_api_key",  ""),
        "deepseek_model":    kv.get("deepseek_model",    "deepseek-chat"),
        "deepseek_base_url": kv.get("deepseek_base_url", "https://api.deepseek.com/v1"),
    }


@router.post("/ai-settings")
async def save_ai_settings(cfg: AIProviderConfig, db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    updates = {
        "ai_provider":       cfg.provider,
        "deepseek_api_key":  cfg.deepseek_api_key or "",
        "deepseek_model":    cfg.deepseek_model,
        "deepseek_base_url": cfg.deepseek_base_url,
    }
    for key, value in updates.items():
        row = (await db.execute(select(SystemSetting).where(SystemSetting.key == key))).scalar_one_or_none()
        if row:
            row.value      = value
            row.updated_at = datetime.utcnow()
        else:
            db.add(SystemSetting(key=key, value=value))
    await db.commit()

    # Invalidate in-memory provider cache so next request picks up new settings
    from services.localai import invalidate_provider_cache
    invalidate_provider_cache()

    return {"ok": True, "provider": cfg.provider}


@router.post("/ai-settings/test")
async def test_ai_connection(db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    """Send a quick ping to the active provider to verify connectivity."""
    from services.localai import _load_provider_config, _call_model
    cfg = await _load_provider_config()
    provider = cfg.get("provider", "ollama")
    model    = cfg.get("deepseek_model", "deepseek-chat") if provider == "deepseek" else "qwen2.5:7b"
    try:
        reply = await _call_model(model, [
            {"role": "system", "content": "Reply with only: OK"},
            {"role": "user",   "content": "ping"},
        ], cfg)
        return {"ok": True, "provider": provider, "model": model, "reply": reply[:80]}
    except Exception as e:
        return {"ok": False, "provider": provider, "error": str(e)}
