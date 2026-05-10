from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.tenant import Tenant
from app.schemas.tenant import TenantRead, TenantUpdate

router = APIRouter()


@router.get("/tenant", response_model=TenantRead)
async def get_tenant_settings(
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, "Mandant nicht gefunden")
    return tenant


@router.patch("/tenant", response_model=TenantRead)
async def update_tenant_settings(
    body: TenantUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404, "Mandant nicht gefunden")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(tenant, key, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant
