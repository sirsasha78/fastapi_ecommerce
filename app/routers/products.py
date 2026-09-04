from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update

from app.db_depends import SessionDep
from app.models import Category as CategoryModel
from app.models import Product as ProductModel
from app.schemas import Product as ProductSchema
from app.schemas import ProductCreate

router = APIRouter(
    prefix="/products",
    tags=["products"],
)


async def get_product_or_404(product_id: int, db: SessionDep) -> ProductModel:
    """Вспомогательная функция для получения продукта"""
    product = db.scalars(
        select(ProductModel).where(
            ProductModel.id == product_id, ProductModel.is_active.is_(True)
        )
    ).first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продукт не найден или неактивен",
        )

    return product


async def get_category_or_404(category_id: int, db: SessionDep) -> CategoryModel:
    """Вспомогательная функция для получения категории"""

    category = db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == category_id, CategoryModel.is_active.is_(True)
        )
    ).first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена или неактивна",
        )

    return category


async def check_category_from_product(product: ProductCreate, db: SessionDep) -> CategoryModel:
    """Вспомогательная функция для получения категории из тела запроса."""

    category = db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id, CategoryModel.is_active.is_(True)
        )
    ).first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория не найдена или неактивна",
        )

    return category


ProductDep = Annotated[ProductModel, Depends(get_product_or_404)]
CategoryDep = Annotated[CategoryModel, Depends(get_category_or_404)]
ProductCategoryDep = Annotated[CategoryModel, Depends(check_category_from_product)]


@router.get("/", response_model=list[ProductSchema])
async def get_all_products(db: SessionDep) -> Sequence[ProductModel]:
    """Возвращает список всех товаров."""

    products = db.scalars(select(ProductModel).where(ProductModel.is_active.is_(True))).all()

    return products


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate, db: SessionDep, _category: ProductCategoryDep
) -> ProductModel:
    """Создаёт новый товар."""

    db_product = ProductModel(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return db_product


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(
    category_id: int, db: SessionDep, _category: CategoryDep
) -> Sequence[ProductModel]:
    """Возвращает список товаров в указанной категории по её ID."""

    products = db.scalars(
        select(ProductModel).where(
            ProductModel.category_id == category_id, ProductModel.is_active.is_(True)
        )
    ).all()

    return products


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product: ProductDep) -> ProductModel:
    """Возвращает детальную информацию о товаре по его ID."""

    return product


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(
    product_id: int, product_create: ProductCreate, db: SessionDep, product: ProductDep
) -> ProductModel:
    """Обновляет товар по его ID."""

    await check_category_from_product(product_create, db)

    db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product_create.model_dump())
    )
    db.commit()
    db.refresh(product)

    return product


@router.delete("/{product_id}")
async def delete_product(db: SessionDep, product: ProductDep) -> dict[str, str]:
    """Удаляет товар по его ID."""

    product.is_active = False
    db.commit()

    return {"status": "success", "message": "Продукт помечен как неактивный"}
