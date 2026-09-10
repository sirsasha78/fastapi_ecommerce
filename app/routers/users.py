from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.auth import create_access_token, create_refresh_token, hash_password, verify_password
from app.config import ALGORITHM, SECRET_KEY
from app.db_depends import AsyncSessionDep
from app.models.users import User as UserModel
from app.schemas import RefreshTokenRequest, UserCreate
from app.schemas import User as UserSchema

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

FormDataDep = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user_create: UserCreate, db: AsyncSessionDep) -> UserModel:
    """Регистрирует нового пользователя с ролью 'buyer' или 'seller'."""

    result = await db.scalars(select(UserModel).where(UserModel.email == user_create.email))
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email уже зарегистрирован",
        )

    user = UserModel(
        email=user_create.email,
        hashed_password=hash_password(user_create.password),
        role=user_create.role,
    )

    db.add(user)
    await db.commit()

    return user


@router.post("/token")
async def login(form_data: FormDataDep, db: AsyncSessionDep) -> dict[str, str]:
    """Аутентифицирует пользователя и возвращает access_token и refresh_token."""

    result = await db.scalars(
        select(UserModel).where(
            UserModel.email == form_data.username, UserModel.is_active.is_(True)
        )
    )
    user = result.first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email, "role": user.role, "id": user.id})
    refresh_token = create_refresh_token(
        data={"sub": user.email, "role": user.role, "id": user.id}
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh-token")
async def refresh_token(body: RefreshTokenRequest, db: AsyncSessionDep) -> dict[str, str]:
    """Обновляет refresh-токен, принимая старый refresh-токен в теле запроса."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен обновления",
        headers={"WWW-Authenticate": "Bearer"},
    )

    old_refresh_token = body.refresh_token

    try:
        payload = jwt.decode(old_refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")

        if email is None or token_type != "refresh":
            raise credentials_exception

    except jwt.ExpiredSignatureError:
        raise credentials_exception from None

    except jwt.PyJWTError:
        raise credentials_exception from None

    result = await db.scalars(
        select(UserModel).where(UserModel.email == email, UserModel.is_active.is_(True))
    )
    user = result.first()
    if user is None:
        raise credentials_exception

    new_refresh_token = create_refresh_token(
        data={"sub": user.email, "role": user.role, "id": user.id}
    )

    return {
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
