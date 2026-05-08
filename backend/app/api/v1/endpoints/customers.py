from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerListResponse, CustomerRead, CustomerUpdate

router = APIRouter()


async def _next_customer_no(db: AsyncSession, tenant_id: int) -> str:
    result = await db.execute(
        select(func.count()).select_from(Customer).where(Customer.tenant_id == tenant_id)
    )
    count = result.scalar_one()
    return f"K{count + 1:04d}"


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: str | None = Query(None),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> CustomerListResponse:
    q = select(Customer).where(Customer.tenant_id == tenant_id)
    if search:
        like = f"%{search}%"
        q = q.where(
            or_(
                Customer.name.ilike(like),
                Customer.email.ilike(like),
                Customer.customer_no.ilike(like),
                Customer.phone.ilike(like),
            )
        )
    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    items = (
        await db.execute(q.order_by(Customer.name).offset(skip).limit(limit))
    ).scalars().all()
    return CustomerListResponse(
        items=[CustomerRead.model_validate(c) for c in items], total=total
    )


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Customer:
    customer = Customer(
        **body.model_dump(),
        tenant_id=tenant_id,
        customer_no=await _next_customer_no(db, tenant_id),
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Customer:
    customer = await _get_or_404(db, customer_id, tenant_id)
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Customer:
    customer = await _get_or_404(db, customer_id, tenant_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> None:
    customer = await _get_or_404(db, customer_id, tenant_id)
    await db.delete(customer)
    await db.commit()


async def _get_or_404(db: AsyncSession, customer_id: int, tenant_id: int) -> Customer:
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.tenant_id == tenant_id
        )
    )
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden")
    return customer
