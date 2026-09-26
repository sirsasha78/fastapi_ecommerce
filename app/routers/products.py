import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import desc, func, select, update

from app.auth import CurrentSellerDep
from app.db_depends import AsyncSessionDep
from app.models.categories import Category as CategoryModel
from app.models.products import Product as ProductModel
from app.models.reviews import Review as ReviewModel
from app.schemas import Product as ProductSchema
from app.schemas import ProductCreate, ProductList, ReviewRead

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media" / "products"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 2 * 1024 * 1024

router = APIRouter(
    prefix="/products",
    tags=["products-v1"],
)


async def save_product_image(file: UploadFile) -> str:
    """Сохраняет изображение товара и возвращает относительный URL."""

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Разрешены только изображения в форматах JPG, PNG или WebP",
        )
    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Изображение слишком большое",
        )

    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    file_name = f"{uuid.uuid4()}{extension}"
    file_path = MEDIA_ROOT / file_name
    file_path.write_bytes(content)

    return f"/media/products/{file_name}"


def remove_product_image(url: str | None) -> None:
    """Удаляет файл изображения, если он существует."""

    if not url:
        return

    relative_path = url.lstrip("/")
    file_path = BASE_DIR / relative_path
    if file_path.exists():
        file_path.unlink()


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
    db: AsyncSessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
    category_id: int | None = Query(None, description="ID категории для фильтрации"),
    search: str | None = Query(None, min_length=1, description="Поиск по названию товара"),
    min_price: float | None = Query(None, ge=0, description="Минимальная цена товара"),
    max_price: float | None = Query(None, ge=0, description="Максимальная цена товара"),
    in_stock: bool | None = Query(
        None, description="true — только товары в наличии, false — только без остатка"
    ),
    seller_id: int | None = Query(None, description="ID продавца для фильтрации"),
) -> ProductList:
    """Возвращает список всех активных товаров."""

    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price не может быть больше max_price",
        )

    filters: list = [ProductModel.is_active.is_(True)]

    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    if in_stock is not None:
        filters.append(ProductModel.stock > 0 if in_stock else ProductModel.stock == 0)
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)

    total_stmt = select(func.count()).select_from(ProductModel).where(*filters)

    rank_col = None
    if search is not None:
        search_value = search.strip()
        if search_value:
            ts_query = func.websearch_to_tsquery("english", search_value)
            filters.append(ProductModel.tsv.op("@@")(ts_query))
            rank_col = func.ts_rank_cd(ProductModel.tsv, ts_query).label("rank")
            total_stmt = select(func.count()).select_from(ProductModel).where(*filters)
    total = await db.scalar(total_stmt) or 0

    if rank_col is not None:
        products_stmt = (
            select(ProductModel, rank_col)
            .where(*filters)
            .order_by(desc(rank_col), ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(products_stmt)
        rows = result.all()
        items = [row[0] for row in rows]
    else:
        products_stmt = (
            select(ProductModel)
            .where(*filters)
            .order_by(ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items: list[ProductSchema] = [
            ProductSchema.model_validate(item) for item in (await db.scalars(products_stmt)).all()
        ]

    return ProductList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: Annotated[ProductCreate, Form(media_type="multipart/form-data")],
    db: AsyncSessionDep,
    _category: ProductCategoryDep,
    current_user: CurrentSellerDep,
) -> ProductSchema:
    """Создаёт новый товар, привязанный к текущему продавцу (только для 'seller')."""

    image_url = await save_product_image(product.image) if product.image else None

    db_product = ProductModel(
        **product.model_dump(exclude={"image"}),
        seller_id=current_user.id,
        image_url=image_url,
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)

    return ProductSchema.model_validate(db_product)


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
    product_create: Annotated[ProductCreate, Form(media_type="multipart/form-data")],
    db: AsyncSessionDep,
    product: ProductDep,
    current_user: CurrentSellerDep,
) -> ProductSchema:
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
        .values(**product_create.model_dump(exclude={"image"}))
    )

    if product_create.image:
        remove_product_image(product.image_url)
        product.image_url = await save_product_image(product_create.image)

    await db.commit()
    await db.refresh(product)

    return ProductSchema.model_validate(product)


@router.delete("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def delete_product(
    db: AsyncSessionDep, product: ProductDep, current_user: CurrentSellerDep
) -> ProductSchema:
    """
    Выполняет мягкое удаление товара, если он принадлежит текущему продавцу (только для 'seller').
    """

    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы можете удалять только свои собственные продукты",
        )

    remove_product_image(product.image_url)

    product.image_url = None
    product.is_active = False
    await db.commit()
    await db.refresh(product)

    return ProductSchema.model_validate(product)
