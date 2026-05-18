from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid, traceback
from models import ChatRequest, ChatResponse, Conversation, UnansweredQuestion
from services.localai import query_localai, extract_classification, check_localai_health
from services.retrieval import build_context
from services.company_search import get_company_info, detect_company_query
from services.dynamic_api import fetch_dynamic_data, fetch_dynamic_data_with_parser
from database import get_db

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

    # 2. If company detected → try dynamic endpoints first
    if symbol:
        dynamic_ctx = await fetch_dynamic_data_with_parser(db, message, symbol)
        if dynamic_ctx:
            context    = dynamic_ctx
            source     = "knowledge_base"
            references = [f"Dynamic API: {symbol}"]

    # 3. If no dynamic data → try company search (MSSQL + MSX.om)
    if not context and symbol:
        company_ctx = await get_company_info(db, message)
        if company_ctx:
            context    = company_ctx
            source     = "knowledge_base"
            references = [f"MSX.om: {symbol}"]

    # 4. Fall back to FAQ / knowledge base
    if not context:
        context, source, references = await build_context(db, message)

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
