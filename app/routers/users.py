from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.auth import hash_password
from app.db_depends import AsyncSessionDep
from app.models.users import User as UserModel
from app.schemas import User as UserSchema
from app.schemas import UserCreate

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


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
