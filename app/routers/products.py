from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select, update

from app.auth import CurrentSellerDep
from app.db_depends import AsyncSessionDep
from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.reviews import Review as ReviewModel
from app.schemas import Product as ProductSchema
from app.schemas import ProductCreate, ProductList, ReviewRead

router = APIRouter(
    prefix="/products",
    tags=["products"],
)


async def get_product_or_404(product_id: int, db: AsyncSessionDep) -> ProductModel:
    """Вспомогательная функция для получения продукта"""

    result = await db.scalars(
        select(ProductModel).where(
            ProductModel.id == product_id, ProductModel.is_active.is_(True)
        )
    )
    product = result.first()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продукт не найден или неактивен",
        )

    category_result = await db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id, CategoryModel.is_active.is_(True)
        )
    )
    category = category_result.first()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория не найдена или неактивна",
        )

    return product


async def get_category_or_404(category_id: int, db: AsyncSessionDep) -> CategoryModel:
    """Вспомогательная функция для получения категории"""

    result = await db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == category_id, CategoryModel.is_active.is_(True)
        )
    )
    category = result.first()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена или неактивна",
        )

    return category


async def check_category_from_product(
    product: ProductCreate, db: AsyncSessionDep
) -> CategoryModel:
    """Вспомогательная функция для получения категории из тела запроса."""

    result = await db.scalars(
        select(CategoryModel).where(
            CategoryModel.id == product.category_id, CategoryModel.is_active.is_(True)
        )
    )
    category = result.first()

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Категория не найдена или неактивна",
        )

    return category


ProductDep = Annotated[ProductModel, Depends(get_product_or_404)]
CategoryDep = Annotated[CategoryModel, Depends(get_category_or_404)]
ProductCategoryDep = Annotated[CategoryModel, Depends(check_category_from_product)]


@router.get("/", response_model=ProductList)
async def get_all_products(
    db: AsyncSessionDep, page: int = Query(1, ge=1), page_size: int = Query(20, le=100)
) -> ProductList:
    """Возвращает список всех активных товаров."""

    total_stmt = (
        select(func.count()).select_from(ProductModel).where(ProductModel.is_active.is_(True))
    )
    total = await db.scalar(total_stmt) or 0

    product_stmt = await db.scalars(
        select(ProductModel)
        .where(ProductModel.is_active.is_(True))
        .order_by(ProductModel.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [ProductSchema.model_validate(p) for p in product_stmt.all()]

    return ProductList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: AsyncSessionDep,
    _category: ProductCategoryDep,
    current_user: CurrentSellerDep,
) -> ProductModel:
    """Создаёт новый товар, привязанный к текущему продавцу (только для 'seller')."""

    db_product = ProductModel(**product.model_dump(), seller_id=current_user.id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)

    return db_product


@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(
    category_id: int, db: AsyncSessionDep, _category: CategoryDep
) -> list[ProductModel]:
    """Возвращает список товаров в указанной категории по её ID."""

    result = await db.scalars(
        select(ProductModel).where(
            ProductModel.category_id == category_id, ProductModel.is_active.is_(True)
        )
    )
    products = result.all()

    return list(products)


@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product: ProductDep) -> ProductModel:
    """Возвращает детальную информацию о товаре по его ID."""

    return product


@router.get("/{product_id}/reviews", response_model=list[ReviewRead])
async def get_reviews_by_product(db: AsyncSessionDep, product: ProductDep) -> list[ReviewModel]:
    """Получение отзывов о конкретном товаре"""

    result = await db.scalars(
        select(ReviewModel)
        .where(ReviewModel.product_id == product.id, ReviewModel.is_active.is_(True))
        .order_by(desc(ReviewModel.comment_date))
    )
    return list(result.all())


@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(
    product_id: int,
    product_create: ProductCreate,
    db: AsyncSessionDep,
    product: ProductDep,
    current_user: CurrentSellerDep,
) -> ProductModel:
    """Обновляет товар, если он принадлежит текущему продавцу (только для 'seller')."""

    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете обновлять только свои собственные продукты",
        )

    await check_category_from_product(product_create, db)

    await db.execute(
        update(ProductModel)
        .where(ProductModel.id == product_id)
        .values(**product_create.model_dump())
    )
    await db.commit()
    await db.refresh(product)

    return product


@router.delete("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def delete_product(
    db: AsyncSessionDep, product: ProductDep, current_user: CurrentSellerDep
) -> ProductModel:
    """
    Выполняет мягкое удаление товара, если он принадлежит текущему продавцу (только для 'seller').
    """

    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете удалять только свои собственные продукты",
        )

    product.is_active = False
    await db.commit()
    await db.refresh(product)

    return product
