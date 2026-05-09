from fastapi import APIRouter

from app.api.v1.endpoints import auth, customers, health, materials, quotes, suppliers

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(suppliers.router, prefix="/suppliers", tags=["suppliers"])
api_router.include_router(materials.router, prefix="/materials", tags=["materials"])
api_router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
