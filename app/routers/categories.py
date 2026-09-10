from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update

from app.auth import CurrentAdminDep
from app.db_depends import AsyncSessionDep
from app.models.categories import Category as CategoryModel
from app.schemas import Category as CategorySchema
from app.schemas import CategoryCreate

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


@router.get("/", response_model=list[CategorySchema])
async def get_all_categories(db: AsyncSessionDep) -> list[CategoryModel]:
    """Возвращает список всех категорий товаров."""

    result = await db.scalars(select(CategoryModel).where(CategoryModel.is_active.is_(True)))
    categories = result.all()

    return list(categories)


@router.post("/", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate, db: AsyncSessionDep, _current_user: CurrentAdminDep
) -> CategoryModel:
    """Создаёт новую категорию."""

    if category.parent_id is not None:
        stmt = select(CategoryModel).where(
            CategoryModel.id == category.parent_id, CategoryModel.is_active.is_(True)
        )
        result = await db.scalars(stmt)
        parent = result.first()
        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Родительская категория не найдена",
            )

    db_category = CategoryModel(**category.model_dump())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)

    return db_category


@router.put("/{category_id}", response_model=CategorySchema)
async def update_category(
    category_id: int,
    category: CategoryCreate,
    db: AsyncSessionDep,
    _current_user: CurrentAdminDep,
) -> CategoryModel | None:
    """Обновляет категорию по её ID."""

    result = await db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == category_id, CategoryModel.is_active.is_(True)
        )
    )
    db_category = result.first()

    if db_category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена",
        )

    if category.parent_id is not None:
        stmt_parent = select(CategoryModel).where(
            CategoryModel.id == category.parent_id, CategoryModel.is_active.is_(True)
        )
        parent_result = await db.scalars(stmt_parent)
        parent = parent_result.first()

        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Родительская категория не найдена",
            )
        if parent.id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Категория не может быть родительской для самой себя",
            )

    await db.execute(
        update(CategoryModel)
        .where(CategoryModel.id == category_id)
        .values(**category.model_dump())
    )
    await db.commit()
    await db.refresh(db_category)

    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_200_OK, response_model=CategorySchema)
async def delete_category(
    category_id: int, db: AsyncSessionDep, _current_user: CurrentAdminDep
) -> CategoryModel:
    """Удаляет категорию по её ID."""

    result = await db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == category_id, CategoryModel.is_active.is_(True)
        )
    )
    category = result.first()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена",
        )

    category.is_active = False
    await db.commit()
    await db.refresh(category)

    return category
