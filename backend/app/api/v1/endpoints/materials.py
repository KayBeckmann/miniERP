from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.material import Material
from app.schemas.material import MaterialCreate, MaterialListResponse, MaterialRead, MaterialUpdate

router = APIRouter()


@router.get("", response_model=MaterialListResponse)
async def list_materials(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: str | None = Query(None),
    active_only: bool = Query(False),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> MaterialListResponse:
    q = select(Material).where(Material.tenant_id == tenant_id)
    if active_only:
        q = q.where(Material.active.is_(True))
    if search:
        like = f"%{search}%"
        q = q.where(
            or_(
                Material.name.ilike(like),
                Material.sku.ilike(like),
                Material.category.ilike(like),
            )
        )
    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    items = (
        await db.execute(
            q.order_by(Material.usage_count.desc(), Material.name).offset(skip).limit(limit)
        )
    ).scalars().all()
    return MaterialListResponse(
        items=[MaterialRead.model_validate(m) for m in items], total=total
    )


@router.post("", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
async def create_material(
    body: MaterialCreate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Material:
    material = Material(**body.model_dump(), tenant_id=tenant_id)
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


@router.get("/{material_id}", response_model=MaterialRead)
async def get_material(
    material_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Material:
    return await _get_or_404(db, material_id, tenant_id)


@router.patch("/{material_id}", response_model=MaterialRead)
async def update_material(
    material_id: int,
    body: MaterialUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Material:
    material = await _get_or_404(db, material_id, tenant_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(material, key, value)
    await db.commit()
    await db.refresh(material)
    return material


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> None:
    material = await _get_or_404(db, material_id, tenant_id)
    await db.delete(material)
    await db.commit()


async def _get_or_404(db: AsyncSession, material_id: int, tenant_id: int) -> Material:
    result = await db.execute(
        select(Material).where(
            Material.id == material_id, Material.tenant_id == tenant_id
        )
    )
    material = result.scalars().first()
    if not material:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden")
    return material
