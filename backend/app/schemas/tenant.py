from pydantic import BaseModel


class TenantRead(BaseModel):
    id: int
    code: str
    name: str
    address: str | None = None
    iban: str | None = None
    pdf_color: str = "#1976D2"
    pdf_footer_text: str | None = None
    pdf_show_bank_details: bool = True
    pdf_accent_secondary: str = "#E3F2FD"

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    iban: str | None = None
    pdf_color: str | None = None
    pdf_footer_text: str | None = None
    pdf_show_bank_details: bool | None = None
    pdf_accent_secondary: str | None = None
