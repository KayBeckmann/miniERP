import csv
import io
import json
import zipfile
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.customer import Customer
from app.models.invoice import Invoice, Payment
from app.models.order import Order, TimeEntry
from app.models.quote import Quote
from app.models.supplier_invoice import SupplierInvoice
from app.models.tenant import Tenant

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> dict:
    quotes_open = (await db.execute(
        select(Quote).where(Quote.tenant_id == tenant_id, Quote.status.in_(["draft", "sent"]))
    )).scalars().all()

    orders_open = (await db.execute(
        select(Order).where(Order.tenant_id == tenant_id, Order.status.in_(["open", "in_progress"]))
    )).scalars().all()

    invoices = (await db.execute(
        select(Invoice).where(Invoice.tenant_id == tenant_id)
    )).scalars().all()

    invoices_open = [i for i in invoices if i.status == "sent"]
    invoices_overdue = [
        i for i in invoices
        if i.status == "sent" and i.due_date and i.due_date < date.today()
    ]

    today = date.today()
    month_start = today.replace(day=1)
    month_hours_result = await db.execute(
        select(TimeEntry).join(Order).where(
            Order.tenant_id == tenant_id,
            TimeEntry.entry_date >= month_start,
        )
    )
    month_hours = sum(float(e.hours) for e in month_hours_result.scalars().all())

    return {
        "quotes_open": len(quotes_open),
        "orders_open": len(orders_open),
        "invoices_open": len(invoices_open),
        "invoices_open_total": str(sum(Decimal(i.total) - Decimal(i.paid_amount) for i in invoices_open)),
        "invoices_overdue": len(invoices_overdue),
        "hours_this_month": round(month_hours, 2),
    }


@router.get("/export/tax")
async def export_tax(
    period_from: date = Query(...),
    period_to: date = Query(...),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Response:
    tenant = await db.get(Tenant, tenant_id)
    tenant_code = tenant.code if tenant else "unknown"

    # Ausgangsrechnungen
    invoices = (await db.execute(
        select(Invoice).options(selectinload(Invoice.payments), selectinload(Invoice.customer))
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_date >= period_from,
            Invoice.invoice_date <= period_to,
            Invoice.status != "draft",
        )
        .order_by(Invoice.invoice_date)
    )).scalars().all()

    # Zahlungen im Zeitraum
    payments = (await db.execute(
        select(Payment).join(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Payment.payment_date >= period_from,
            Payment.payment_date <= period_to,
        )
        .order_by(Payment.payment_date)
    )).scalars().all()

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # ausgangsrechnungen.csv
        ar_buf = io.StringIO()
        w = csv.writer(ar_buf, delimiter=";")
        w.writerow(["Datum", "Rechnungsnr.", "Sparte", "Kunde", "Art", "Status",
                    "Netto", "USt", "Brutto", "Zahlung am", "Bezahlt"])
        for inv in invoices:
            customer_name = inv.customer.name if inv.customer else str(inv.customer_id)
            paid_at = inv.paid_at.strftime("%d.%m.%Y") if inv.paid_at else ""
            w.writerow([
                inv.invoice_date.strftime("%d.%m.%Y"), inv.invoice_no, tenant_code,
                customer_name, inv.kind, inv.status,
                str(inv.subtotal), str(inv.vat_total), str(inv.total),
                paid_at, str(inv.paid_amount),
            ])
        zf.writestr("ausgangsrechnungen.csv", ar_buf.getvalue())

        # zahlungen.csv
        pay_buf = io.StringIO()
        w2 = csv.writer(pay_buf, delimiter=";")
        w2.writerow(["Datum", "Rechnungsnr.", "Betrag", "Methode", "Bankreferenz", "Notiz"])
        for p in payments:
            inv_no = p.invoice.invoice_no if hasattr(p, "invoice") and p.invoice else str(p.invoice_id)
            w2.writerow([
                p.payment_date.strftime("%d.%m.%Y"), inv_no,
                str(p.amount), p.method, p.bank_ref or "", p.note or "",
            ])
        zf.writestr("zahlungen.csv", pay_buf.getvalue())

        # manifest.json
        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tenant_id": tenant_id,
            "tenant_code": tenant_code,
            "period_from": period_from.isoformat(),
            "period_to": period_to.isoformat(),
            "invoices_count": len(invoices),
            "payments_count": len(payments),
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

    zip_buf.seek(0)
    filename = f"steuerberater_{tenant_code}_{period_from}_{period_to}.zip"
    return Response(
        content=zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/margin")
async def margin_report(
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[dict]:
    orders = (await db.execute(
        select(Order)
        .options(
            selectinload(Order.time_entries),
            selectinload(Order.customer),
        )
        .where(Order.tenant_id == tenant_id)
        .order_by(Order.created_at.desc())
    )).scalars().all()

    # Load invoices grouped by order_id
    invoices_result = (await db.execute(
        select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.order_id.is_not(None))
    )).scalars().all()
    inv_by_order: dict[int, list[Invoice]] = {}
    for inv in invoices_result:
        inv_by_order.setdefault(inv.order_id, []).append(inv)  # type: ignore[arg-type]

    rows = []
    for o in orders:
        hours_total = float(sum(e.hours for e in o.time_entries))
        hours_billable = float(sum(e.hours for e in o.time_entries if e.billable))
        invoiced_total = float(sum(Decimal(i.total) for i in inv_by_order.get(o.id, [])))
        # Estimate time cost: use hourly_rate on entry if set, else 0 (no default rate in model)
        time_cost = float(sum(
            e.hours * (e.hourly_rate or Decimal("0"))
            for e in o.time_entries if e.billable
        ))
        marge = invoiced_total - time_cost
        rows.append({
            "order_id": o.id,
            "order_no": o.order_no,
            "title": o.title,
            "customer": o.customer.name if o.customer else "",
            "status": o.status,
            "hours_total": round(hours_total, 2),
            "hours_billable": round(hours_billable, 2),
            "time_cost": round(time_cost, 2),
            "invoiced_total": round(invoiced_total, 2),
            "marge": round(marge, 2),
        })
    return rows


@router.get("/vat-preview")
async def vat_preview(
    period_from: date = Query(...),
    period_to: date = Query(...),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> dict:
    invoices = (await db.execute(
        select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_date >= period_from,
            Invoice.invoice_date <= period_to,
            Invoice.status.notin_(["draft", "cancelled"]),
        )
    )).scalars().all()

    supplier_invoices = (await db.execute(
        select(SupplierInvoice).where(
            SupplierInvoice.tenant_id == tenant_id,
            SupplierInvoice.invoice_date >= period_from,
            SupplierInvoice.invoice_date <= period_to,
            SupplierInvoice.status.in_(["confirmed", "paid"]),
        )
    )).scalars().all()

    soll_ust = float(sum(Decimal(str(i.vat_total)) for i in invoices))
    vorsteuer = float(sum(
        Decimal(str(si.vat_total)) for si in supplier_invoices if si.vat_total is not None
    ))
    zahllast = soll_ust - vorsteuer

    return {
        "period_from": period_from.isoformat(),
        "period_to": period_to.isoformat(),
        "soll_ust": round(soll_ust, 2),
        "vorsteuer": round(vorsteuer, 2),
        "zahllast": round(zahllast, 2),
        "invoices_count": len(invoices),
        "supplier_invoices_count": len(supplier_invoices),
    }
