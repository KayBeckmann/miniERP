from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _seed_initial_data()
    yield


async def _seed_initial_data() -> None:
    async with AsyncSessionLocal() as session:
        existing = (await session.execute(select(Tenant))).scalars().first()
        if existing:
            return

        bau = Tenant(
            code="bau",
            name="Bauunternehmen",
            invoice_number_prefix="BAU",
            quote_number_prefix="ABAU",
        )
        huf = Tenant(
            code="huf",
            name="Hufbearbeitung",
            invoice_number_prefix="HUF",
            quote_number_prefix="AHUF",
        )
        session.add_all([bau, huf])
        await session.flush()

        admin = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            password_hash=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            role="admin",
            is_active=True,
            default_tenant_id=bau.id,
        )
        session.add(admin)
        await session.commit()


app = FastAPI(
    title="miniERP",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
