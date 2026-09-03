from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status
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


@router.get("/", response_model=list[ProductSchema])
async def get_all_products(db: SessionDep) -> Sequence[ProductModel]:
    """Возвращает список всех товаров."""

    stmt = select(ProductModel).where(ProductModel.is_active.is_(True))
    products = db.scalars(stmt).all()

    return products


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, db: SessionDep) -> ProductModel:
    """Создаёт новый товар."""

    stmt = select(CategoryModel).where(
        CategoryModel.id == product.category_id, CategoryModel.is_active.is_(True)
    )
    category = db.scalars(stmt).first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория не найдена или неактивна",
        )

    db_product = ProductModel(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return db_product


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(category_id: int, db: SessionDep) -> Sequence[ProductModel]:
    """Возвращает список товаров в указанной категории по её ID."""

    stmt_category = select(CategoryModel).where(
        CategoryModel.id == category_id, CategoryModel.is_active.is_(True)
    )
    category = db.scalars(stmt_category).first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена или неактивна",
        )

    stmt = select(ProductModel).where(
        ProductModel.category_id == category_id, ProductModel.is_active.is_(True)
    )
    products = db.scalars(stmt).all()

    return products


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: SessionDep) -> ProductModel:
    """Возвращает детальную информацию о товаре по его ID."""

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

    return product


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(product_id: int, product: ProductCreate, db: SessionDep) -> ProductModel:
    """Обновляет товар по его ID."""

    db_product = db.scalars(
        select(ProductModel).where(
            ProductModel.id == product_id, ProductModel.is_active.is_(True)
        )
    ).first()
    if db_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продукт не найден или неактивен",
        )

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

    db.execute(
        update(ProductModel).where(ProductModel.id == product_id).values(**product.model_dump())
    )
    db.commit()
    db.refresh(db_product)

    return db_product


@router.delete("/{product_id}")
async def delete_product(product_id: int) -> dict[str, str]:
    """Удаляет товар по его ID."""

    return {"message": f"Товар с ID {product_id} удален (заглушка)"}
