from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select

from app.config import ALGORITHM, SECRET_KEY
from app.db_depends import AsyncSessionDep
from app.models.users import User as UserModel

password_hash = PasswordHash.recommended()

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")

TokenDep = Annotated[str, Depends(oauth2_scheme)]


def hash_password(password: str) -> str:
    """Преобразует пароль в безопасный хеш."""

    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, соответствует ли введённый пароль сохранённому хешу."""

    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Создаёт JWT с payload (sub, role, id, exp)."""

    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update(
        {
            "exp": expire,
            "token_type": "access",
        }
    )

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Создаёт refresh-токен с длительным сроком действия и token_type="refresh"."""

    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {
            "exp": expire,
            "token_type": "refresh",
        }
    )

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: TokenDep, db: AsyncSessionDep) -> UserModel:
    """Проверяет JWT и возвращает пользователя из базы."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")

        if email is None or token_type != "access":
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия токена истёк",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError:
        raise credentials_exception from None

    result = await db.scalars(
        select(UserModel).where(UserModel.email == email, UserModel.is_active.is_(True))
    )
    user = result.first()

    if user is None:
        raise credentials_exception

    return user


CurrentUserDep = Annotated[UserModel, Depends(get_current_user)]


async def get_current_seller(current_user: CurrentUserDep) -> UserModel:
    """Проверяет, что пользователь имеет роль 'seller'."""

    if current_user.role != "seller":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только продавцы могут выполнить это действие",
        )

    return current_user


CurrentSellerDep = Annotated[UserModel, Depends(get_current_seller)]


async def get_current_admin(current_user: CurrentUserDep) -> UserModel:
    """Проверяет, что пользователь имеет роль 'admin'."""

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администратры могут выполнить это действие",
        )

    return current_user


CurrentAdminDep = Annotated[UserModel, Depends(get_current_admin)]
