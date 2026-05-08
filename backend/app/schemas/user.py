from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    default_tenant_id: int | None

    model_config = {"from_attributes": True}
