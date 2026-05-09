import datetime as dt
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class OrderCreate(BaseModel):
    customer_id: int
    quote_id: int | None = None
    title: str
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    budget_hours: Decimal | None = None
    budget_material: Decimal | None = None
    notes: str | None = None


class OrderUpdate(BaseModel):
    title: str | None = None
    status: Literal["open", "in_progress", "done", "cancelled"] | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    budget_hours: Decimal | None = None
    budget_material: Decimal | None = None
    notes: str | None = None


class OrderRead(BaseModel):
    id: int
    tenant_id: int
    customer_id: int
    quote_id: int | None
    order_no: str
    title: str
    status: str
    start_date: dt.date | None
    end_date: dt.date | None
    budget_hours: Decimal | None
    budget_material: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    hours_total: float = 0.0
    hours_billable: float = 0.0

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderRead]
    total: int


class TimeEntryCreate(BaseModel):
    entry_date: dt.date
    hours: Decimal
    description: str | None = None
    hourly_rate: Decimal | None = None
    billable: bool = True


class TimeEntryUpdate(BaseModel):
    entry_date: dt.date | None = None
    hours: Decimal | None = None
    description: str | None = None
    hourly_rate: Decimal | None = None
    billable: bool | None = None


class TimeEntryRead(BaseModel):
    id: int
    order_id: int
    user_id: int
    entry_date: dt.date
    hours: Decimal
    description: str | None
    hourly_rate: Decimal | None
    billable: bool
    invoiced: bool
    created_at: datetime

    model_config = {"from_attributes": True}
