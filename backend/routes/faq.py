from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List, Optional
import uuid
from models import FAQ, FAQCreate, FAQUpdate, FAQDoc
from database import get_db
from auth import get_current_admin

router = APIRouter(prefix="/api/faq", tags=["faq"])


def _serialize(faq: FAQ) -> dict:
    return {
        "id": str(faq.id),
        "question": faq.question,
        "answer": faq.answer,
        "category": faq.category,
        "is_active": faq.is_active,
        "created_at": faq.created_at,
        "updated_at": faq.updated_at,
    }


@router.get("", response_model=List[FAQDoc])
async def list_faqs(
    category: Optional[str] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    query = select(FAQ)
    if category:
        query = query.where(FAQ.category == category)
    if active_only:
        query = query.where(FAQ.is_active == True)
    query = query.order_by(FAQ.created_at.desc())
    result = await db.execute(query)
    return [_serialize(f) for f in result.scalars().all()]


@router.get("/public", response_model=List[FAQDoc])
async def list_public_faqs(category: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(FAQ).where(FAQ.is_active == True)
    if category:
        query = query.where(FAQ.category == category)
    result = await db.execute(query)
    return [_serialize(f) for f in result.scalars().all()]


@router.post("", response_model=FAQDoc, status_code=201)
async def create_faq(data: FAQCreate, db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    faq = FAQ(**data.model_dump())
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return _serialize(faq)


@router.put("/{faq_id}", response_model=FAQDoc)
async def update_faq(faq_id: str, data: FAQUpdate, db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    result = await db.execute(select(FAQ).where(FAQ.id == uuid.UUID(faq_id)))
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(faq, k, v)
    faq.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(faq)
    return _serialize(faq)


@router.delete("/{faq_id}")
async def delete_faq(faq_id: str, db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    result = await db.execute(select(FAQ).where(FAQ.id == uuid.UUID(faq_id)))
    faq = result.scalar_one_or_none()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    await db.delete(faq)
    await db.commit()
    return {"deleted": True}
