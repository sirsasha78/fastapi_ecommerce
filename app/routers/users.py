from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.auth import create_access_token, hash_password, verify_password
from app.db_depends import AsyncSessionDep
from app.models.users import User as UserModel
from app.schemas import User as UserSchema
from app.schemas import UserCreate

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
    """Аутентифицирует пользователя и возвращает JWT с email, role и id."""

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

    return {"access_token": access_token, "token_type": "bearer"}
