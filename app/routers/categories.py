from collections.abc import Sequence

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


@router.get("/", response_model=list[CategorySchema])
async def get_all_categories(db: SessionDep) -> Sequence[CategoryModel]:
    """Возвращает список всех категорий товаров."""

    stmt = select(CategoryModel).where(CategoryModel.is_active.is_(True))
    categories = db.scalars(stmt).all()
    print(categories)

    return categories


@router.post("/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(category: CategoryCreate, db: SessionDep) -> CategoryModel:
    """Создаёт новую категорию."""

    if category.parent_id is not None:
        stmt = select(CategoryModel).where(
            CategoryModel.id == category.parent_id, CategoryModel.is_active.is_(True)
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


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
async def delete_category(category_id: int, db: SessionDep) -> dict[str, str]:
    """Удаляет категорию по её ID."""

    stmt = select(CategoryModel).where(
        CategoryModel.id == category_id, CategoryModel.is_active.is_(True)
    )
    category = db.scalars(stmt).first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена",
        )

    category.is_active = False
    db.commit()

    return {"status": "success", "message": "Категория помечена как неактивная"}
