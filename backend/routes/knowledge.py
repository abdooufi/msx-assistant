from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from datetime import datetime
from typing import List, Optional
import uuid
from models import KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseDoc
from database import get_db
from auth import get_current_admin

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _serialize(doc: KnowledgeBase) -> dict:
    return {
        "id": str(doc.id),
        "title": doc.title,
        "content": doc.content,
        "category": doc.category,
        "tags": doc.tags or [],
        "source": doc.source,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


@router.get("", response_model=List[KnowledgeBaseDoc])
async def list_knowledge(
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    query = select(KnowledgeBase)
    if category:
        query = query.where(KnowledgeBase.category == category)
    if search:
        query = query.where(or_(
            KnowledgeBase.title.ilike(f"%{search}%"),
            KnowledgeBase.content.ilike(f"%{search}%"),
        ))
    query = query.order_by(KnowledgeBase.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return [_serialize(d) for d in result.scalars().all()]


@router.post("", response_model=KnowledgeBaseDoc, status_code=201)
async def create_knowledge(
    data: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    doc = KnowledgeBase(**data.model_dump())
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return _serialize(doc)


@router.get("/{doc_id}", response_model=KnowledgeBaseDoc)
async def get_knowledge(doc_id: str, db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(doc_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _serialize(doc)


@router.put("/{doc_id}", response_model=KnowledgeBaseDoc)
async def update_knowledge(
    doc_id: str,
    data: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(doc_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(doc, k, v)
    doc.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(doc)
    return _serialize(doc)


@router.delete("/{doc_id}")
async def delete_knowledge(doc_id: str, db: AsyncSession = Depends(get_db), _: str = Depends(get_current_admin)):
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(doc_id)))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()
    return {"deleted": True}
