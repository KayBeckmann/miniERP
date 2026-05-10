from fastapi import APIRouter

from app.api.v1.endpoints import auth, customers, health, invoices, llm, materials, orders, quotes, reports, settings, supplier_invoices, suppliers

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(materials.router, prefix="/materials", tags=["materials"])
api_router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(supplier_invoices.router, prefix="/supplier-invoices", tags=["supplier-invoices"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
