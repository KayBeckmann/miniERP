from pathlib import Path

import httpx
from jinja2 import Environment, FileSystemLoader

from app.core.config import settings
from app.models.customer import Customer
from app.models.quote import Quote
from app.models.tenant import Tenant

_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "pdf"


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


async def render_quote_pdf(quote: Quote, customer: Customer, tenant: Tenant) -> bytes:
    env = _env()
    template = env.get_template("quote.html")
    html = template.render(quote=quote, customer=customer, tenant=tenant)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.GOTENBERG_URL}/forms/chromium/convert/html",
            files={"files": ("index.html", html.encode("utf-8"), "text/html")},
        )

    if response.status_code != 200:
        raise RuntimeError(f"Gotenberg error {response.status_code}: {response.text[:200]}")

    return response.content


def pdf_path(quote_no: str) -> Path:
    p = Path("/app/uploads/quotes")
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{quote_no}.pdf"
