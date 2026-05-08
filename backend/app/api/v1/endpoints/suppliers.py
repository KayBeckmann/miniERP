from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierListResponse, SupplierRead, SupplierUpdate

router = APIRouter()


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: str | None = Query(None),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> SupplierListResponse:
    q = select(Supplier).where(Supplier.tenant_id == tenant_id)
    if search:
        like = f"%{search}%"
        q = q.where(or_(Supplier.name.ilike(like), Supplier.email.ilike(like)))
    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    items = (
        await db.execute(q.order_by(Supplier.name).offset(skip).limit(limit))
    ).scalars().all()
    return SupplierListResponse(
        items=[SupplierRead.model_validate(s) for s in items], total=total
    )


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    body: SupplierCreate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Supplier:
    supplier = Supplier(**body.model_dump(), tenant_id=tenant_id)
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Supplier:
    return await _get_or_404(db, supplier_id, tenant_id)


@router.patch("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: int,
    body: SupplierUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Supplier:
    supplier = await _get_or_404(db, supplier_id, tenant_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> None:
    supplier = await _get_or_404(db, supplier_id, tenant_id)
    await db.delete(supplier)
    await db.commit()


async def _get_or_404(db: AsyncSession, supplier_id: int, tenant_id: int) -> Supplier:
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id, Supplier.tenant_id == tenant_id
        )
    )
    supplier = result.scalars().first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Lieferant nicht gefunden")
    return supplier
