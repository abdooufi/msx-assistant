from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import Optional
import uuid, traceback
from models import ChatRequest, ChatResponse, Conversation, UnansweredQuestion
from services.localai import query_localai, extract_classification, check_localai_health
from services.retrieval import build_context
from services.company_search import get_company_info, detect_company_query
from services.dynamic_api import fetch_dynamic_data, fetch_dynamic_data_with_parser
from database import get_db

# NotiType codes from GetNotificationsCenter
_NOTI_TYPE_LABELS = {"1": "News", "2": "Event", "3": "Publication", "4": "Special Trade"}
_NOTI_QUERY_KEYWORDS = {
    "special trade": "4", "special trades": "4", "صفقة خاصة": "4", "صفقات خاصة": "4",
    "news": "1",     "أخبار": "1",
    "event": "2",    "events": "2",    "أحداث": "2",
    "publication": "3", "publications": "3", "نشرة": "3",
    "notification": None, "notifications": None, "latest": None,
    "إشعار": None,   "إشعارات": None,
}


def _detect_notification_query(message: str):
    """Return (noti_type_filter | None, True) if message asks about notifications/trades."""
    msg = message.lower()
    for kw, ntype in _NOTI_QUERY_KEYWORDS.items():
        if kw in msg:
            return ntype, True
    return None, False


async def _fetch_notifications_context(symbol: Optional[str], noti_type: Optional[str]) -> Optional[str]:
    """Call GetNotificationsCenter and return formatted context filtered by symbol/type."""
    from services.msx_api import get_notifications_center
    try:
        items = await get_notifications_center()
        if not items or not isinstance(items, list):
            return None

        # Filter by symbol and/or NotiType
        filtered = items
        if symbol:
            sym_upper = symbol.upper()
            filtered = [i for i in filtered if i.get("symbol", "").upper() == sym_upper]
        if noti_type:
            filtered = [i for i in filtered if str(i.get("NotiType", "")) == noti_type]

        if not filtered:
            # If symbol filter returns nothing, try broader match
            if symbol:
                filtered = items[:15] if not noti_type else [i for i in items if str(i.get("NotiType","")) == noti_type][:15]

        if not filtered:
            return None

        label = _NOTI_TYPE_LABELS.get(noti_type, "Notification") if noti_type else "Notification"
        lines = [f"📢 Recent {label} records from MSX Notifications Center:\n"]
        for item in filtered[:10]:
            sym  = item.get("symbol", "")
            name = item.get("LongNameEn", "")
            time = item.get("NotifiTime", item.get("NotifiDateTime", ""))
            title_en = item.get("TitleEn", "")
            title_ar = item.get("TitleAr", "")
            link_en  = item.get("LinkEn", "")
            ntype    = _NOTI_TYPE_LABELS.get(str(item.get("NotiType", "")), "")
            base_url = "https://www.msx.om/"
            full_link = base_url + link_en if link_en and not link_en.startswith("http") else link_en
            lines.append(
                f"• [{time}] {sym} — {name}\n"
                f"  Type: {ntype}\n"
                f"  EN: {title_en}\n"
                f"  AR: {title_ar.strip()}\n"
                f"  Link: {full_link}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        print(f"⚠️ Notifications fetch error: {e}")
        return None

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    session_id = request.session_id or str(uuid.uuid4())
    message    = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    context    = None
    source     = "ai_general"
    references = []

    # 1. Detect company symbol
    symbol = detect_company_query(message)

    # Detect query intent
    _board_kw   = {'chairman','board','director','secretary','management','ceo','coo','members','deputy'}
    is_board_query = any(kw in message.lower() for kw in _board_kw)
    noti_type, is_noti_query = _detect_notification_query(message)

    # 2. Notifications / special trades / news from GetNotificationsCenter
    if is_noti_query:
        noti_ctx = await _fetch_notifications_context(symbol, noti_type)
        if noti_ctx:
            context    = noti_ctx
            source     = "knowledge_base"
            references = ["https://www.msx.om/api.aspx/GetNotificationsCenter"]

    # 3. If company detected → try dynamic endpoints first
    if not context and symbol:
        dynamic_ctx = await fetch_dynamic_data_with_parser(db, message, symbol)
        if dynamic_ctx:
            context    = dynamic_ctx
            source     = "knowledge_base"
            references = [f"Dynamic API: {symbol}"]

    # 4. If no dynamic data → try company search (MSSQL + MSX.om)
    if not context and symbol:
        company_ctx = await get_company_info(db, message)
        if company_ctx:
            context    = company_ctx
            source     = "knowledge_base"
            references = [f"MSX.om: {symbol}"]

    # 5. Fall back to FAQ / knowledge base / RAG
    if not context:
        context, source, references = await build_context(db, message)

    # 5. Board/management queries: always supplement with RAG (scraped snapshot pages
    #    contain chairman/board info that dynamic APIs and MSSQL do not provide)
    elif is_board_query:
        try:
            from services.rag import search_rag
            rag_ctx, rag_srcs, _ = await search_rag(message)
            if rag_ctx:
                context = context + "\n\n" + rag_ctx if context else rag_ctx
                references = list(dict.fromkeys(references + rag_srcs[:2]))
        except Exception as e:
            print(f"⚠️ RAG supplement error: {e}")

    # 5. Query LocalAI
    try:
        print(f"🔄 LocalAI | symbol={symbol} | source={source}")
        ai_result  = await query_localai(
            user_message=message,
            history=[m.model_dump() for m in request.history],
            context=context,
        )
        raw_reply  = ai_result["content"]
    except Exception as e:
        print(f"❌ LocalAI error: {type(e).__name__}: {e}")
        traceback.print_exc()
        raw_reply = (
            "I'm sorry, I'm having trouble connecting to my AI engine right now. "
            "Please contact MSX support directly at www.msx.om.\n[CLASSIFICATION: support]"
        )
        source = "fallback"

    # 6. Extract classification
    clean_reply, classification = extract_classification(raw_reply)

    # 7. Confidence
    confidence = 0.9 if source in ("faq", "knowledge_base") else 0.6
    is_low     = source == "fallback" or "i don't know" in clean_reply.lower()
    if is_low:
        confidence = 0.3
        db.add(UnansweredQuestion(
            question=message, session_id=session_id,
            classification=classification, status="pending"
        ))

    # 8. Save conversation
    result = await db.execute(select(Conversation).where(Conversation.session_id == session_id))
    conv   = result.scalar_one_or_none()
    now    = datetime.utcnow()
    msgs   = [
        {"role": "user",      "content": message,     "timestamp": now.isoformat()},
        {"role": "assistant", "content": clean_reply,  "timestamp": now.isoformat(),
         "source": source, "classification": classification},
    ]
    if conv:
        conv.messages  = (conv.messages or []) + msgs
        conv.updated_at = now
    else:
        conv = Conversation(session_id=session_id, messages=msgs)
        db.add(conv)
    await db.commit()

    return ChatResponse(
        reply=clean_reply, session_id=session_id,
        classification=classification, source=source,
        confidence=confidence, references=references,
    )


@router.get("/health")
async def chat_health():
    ok = await check_localai_health()
    return {"status": "ok", "localai": "connected" if ok else "unavailable"}
