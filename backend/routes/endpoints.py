from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List, Optional
import uuid
from models import ApiEndpoint, ApiEndpointCreate, ApiEndpointUpdate, ApiEndpointDoc
from database import get_db
from auth import get_current_admin

router = APIRouter(prefix="/api/endpoints", tags=["endpoints"])


def _serialize(e: ApiEndpoint) -> dict:
    return {
        "id": str(e.id),
        "name": e.name,
        "description": e.description,
        "url": e.url,
        "method": e.method,
        "body": e.body,
        "headers": e.headers,
        "keywords_en": e.keywords_en or [],
        "keywords_ar": e.keywords_ar or [],
        "category": e.category,
        "is_active": e.is_active,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }


@router.get("", response_model=List[ApiEndpointDoc])
async def list_endpoints(
    category: Optional[str] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    q = select(ApiEndpoint)
    if category:
        q = q.where(ApiEndpoint.category == category)
    if active_only:
        q = q.where(ApiEndpoint.is_active == True)
    q = q.order_by(ApiEndpoint.created_at.desc())
    result = await db.execute(q)
    return [_serialize(e) for e in result.scalars().all()]


@router.get("/public", response_model=List[ApiEndpointDoc])
async def list_public_endpoints(db: AsyncSession = Depends(get_db)):
    """Public endpoint — returns active endpoints for the chat engine."""
    q = select(ApiEndpoint).where(ApiEndpoint.is_active == True)
    result = await db.execute(q)
    return [_serialize(e) for e in result.scalars().all()]


@router.post("", response_model=ApiEndpointDoc, status_code=201)
async def create_endpoint(
    data: ApiEndpointCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    ep = ApiEndpoint(**data.model_dump())
    db.add(ep)
    await db.commit()
    await db.refresh(ep)
    return _serialize(ep)


@router.put("/{ep_id}", response_model=ApiEndpointDoc)
async def update_endpoint(
    ep_id: str,
    data: ApiEndpointUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    result = await db.execute(select(ApiEndpoint).where(ApiEndpoint.id == uuid.UUID(ep_id)))
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(ep, k, v)
    ep.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ep)
    return _serialize(ep)


@router.delete("/{ep_id}")
async def delete_endpoint(
    ep_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    result = await db.execute(select(ApiEndpoint).where(ApiEndpoint.id == uuid.UUID(ep_id)))
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    await db.delete(ep)
    await db.commit()
    return {"deleted": True}


@router.post("/{ep_id}/test")
async def test_endpoint(
    ep_id: str,
    symbol: Optional[str] = "OQEP",
    db: AsyncSession = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    """Test an endpoint with a sample symbol."""
    result = await db.execute(select(ApiEndpoint).where(ApiEndpoint.id == uuid.UUID(ep_id)))
    ep = result.scalar_one_or_none()
    if not ep:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    from services.dynamic_api import call_endpoint
    data = await call_endpoint(ep, symbol=symbol)
    return {"endpoint": ep.name, "symbol": symbol, "result": data}
