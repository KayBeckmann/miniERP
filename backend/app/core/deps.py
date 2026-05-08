from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültiger Token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise exc
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise exc
    return user


async def get_tenant_id(
    x_tenant_id: int | None = Header(default=None, alias="X-Tenant-ID"),
    user: User = Depends(get_current_user),
) -> int:
    if x_tenant_id is not None:
        return x_tenant_id
    if user.default_tenant_id is not None:
        return user.default_tenant_id
    raise HTTPException(status_code=400, detail="Kein Mandant ausgewählt")
