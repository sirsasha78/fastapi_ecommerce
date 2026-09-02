from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.db_depends import SessionDep
from app.models import Category as CategoryModel
from app.models import Product as ProductModel
from app.schemas import Product as ProductSchema
from app.schemas import ProductCreate

router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get("/")
async def get_all_products() -> dict[str, str]:
    """Возвращает список всех товаров."""

    return {"message": "Список всех товаров (заглушка)"}


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


@router.get("/category/{category_id}")
async def get_products_by_category(category_id: int) -> dict[str, str]:
    """Возвращает список товаров в указанной категории по её ID."""

    return {"message": f"Товары в категории {category_id} (заглушка)"}


@router.get("/{product_id}")
async def get_product(product_id: int) -> dict[str, str]:
    """Возвращает детальную информацию о товаре по его ID."""

    return {"message": f"Детали товара {product_id} (заглушка)"}


@router.put("{product_id}")
async def update_product(product_id: int) -> dict[str, str]:
    """Обновляет товар по его ID."""

    return {"message": f"Товар с ID {product_id} обновлен (заглушка)"}


@router.delete("/{product_id}")
async def delete_product(product_id: int) -> dict[str, str]:
    """Удаляет товар по его ID."""

    return {"message": f"Товар с ID {product_id} удален (заглушка)"}
