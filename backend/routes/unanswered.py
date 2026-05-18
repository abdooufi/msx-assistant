from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List, Optional
import uuid
from models import UnansweredQuestion, UnansweredQuestionSchema, UnansweredUpdate
from database import get_db
from auth import get_current_admin

router = APIRouter(prefix="/api/unanswered", tags=["unanswered"])


def _serialize(item: UnansweredQuestion) -> dict:
    return {
        "id": str(item.id),
        "question": item.question,
        "session_id": item.session_id,
        "classification": item.classification,
        "status": item.status,
        "admin_note": item.admin_note,
        "created_at": item.created_at,
    }


@router.get("", response_model=List[UnansweredQuestionSchema])
async def list_unanswered(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    query = select(UnansweredQuestion)
    if status:
        query = query.where(UnansweredQuestion.status == status)
    query = query.order_by(UnansweredQuestion.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return [_serialize(i) for i in result.scalars().all()]


@router.put("/{item_id}", response_model=UnansweredQuestionSchema)
async def update_unanswered(
    item_id: str,
    data: UnansweredUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    result = await db.execute(select(UnansweredQuestion).where(UnansweredQuestion.id == uuid.UUID(item_id)))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    return _serialize(item)


@router.delete("/{item_id}")
async def delete_unanswered(item_id: str, db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    result = await db.execute(select(UnansweredQuestion).where(UnansweredQuestion.id == uuid.UUID(item_id)))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
    return {"deleted": True}
