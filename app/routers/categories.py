from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.db_depends import SessionDep
from app.models.categories import Category as CategoryModel
from app.schemas import Category as CategorySchema
from app.schemas import CategoryCreate

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


@router.get("/")
async def get_all_categories() -> dict[str, str]:
    """Возвращает список всех категорий товаров."""

    return {"message": "Список всех категорий (заглушка)"}


@router.post("/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(category: CategoryCreate, db: SessionDep) -> CategoryModel:
    """Создаёт новую категорию."""

    if category.parent_id is not None:
        stmt = select(CategoryModel).where(
            CategoryModel.id == category.parent_id, CategoryModel.is_active
        )
        parent = db.scalars(stmt).first()
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Родительская категория не найдена",
            )

    db_category = CategoryModel(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)

    return db_category


@router.put("/{category_id}")
async def update_category(category_id: int) -> dict[str, str]:
    """Обновляет категорию по её ID."""

    return {"message": f"Категория с ID {category_id} обновлена (заглушка)"}


@router.delete("/{category_id}")
async def delete_category(category_id: int) -> dict[str, str]:
    """Удаляет категорию по её ID."""

    return {"message": f"Категория с ID {category_id} удалена (заглушка)"}
