from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import NumberSequence
from app.models.tenant import Tenant


async def next_number(db: AsyncSession, tenant_id: int, kind: str) -> str:
    year = datetime.now().year

    result = await db.execute(
        select(NumberSequence)
        .where(
            NumberSequence.tenant_id == tenant_id,
            NumberSequence.kind == kind,
            NumberSequence.year == year,
        )
        .with_for_update()
    )
    seq = result.scalars().first()

    if seq is None:
        seq = NumberSequence(tenant_id=tenant_id, kind=kind, year=year, next_value=1)
        db.add(seq)

    tenant = await db.get(Tenant, tenant_id)
    prefix = _prefix(tenant, kind)
    value = seq.next_value
    seq.next_value += 1

    return f"{prefix}-{year}-{value:03d}"


def _prefix(tenant: Tenant | None, kind: str) -> str:
    if tenant is None:
        return kind.upper()[:3]
    if kind == "quote":
        return tenant.quote_number_prefix or "A"
    if kind == "invoice":
        return tenant.invoice_number_prefix or "R"
    return kind.upper()[:3]
