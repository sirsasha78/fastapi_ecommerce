from decimal import Decimal

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.auth import CurrentUserDep
from app.db_depends import AsyncSessionDep
from app.models.cart_items import CartItem as CartItemModel
from app.models.products import Product as ProductModel
from app.schemas import Cart as CartSchema
from app.schemas import CartItem as CartItemSchema
from app.schemas import CartItemCreate, CartItemUpdate

router = APIRouter(
    prefix="/cart",
    tags=["cart"],
)


async def _ensure_product_available(db: AsyncSessionDep, product_id: int) -> None:
    """
    Функция для провеки, что товар с указанным product_id существует в базе данных и активен.
    """

    result = await db.scalars(
        select(ProductModel).where(
            ProductModel.id == product_id, ProductModel.is_active.is_(True)
        )
    )
    product = result.first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Продукт не найден или неактивен",
        )


async def _get_cart_item(
    db: AsyncSessionDep, user_id: int, product_id: int
) -> CartItemModel | None:
    """Функция для поиска товара в корзине текущего пользователя по product_id."""

    result = await db.scalars(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(CartItemModel.user_id == user_id, CartItemModel.product_id == product_id)
    )

    return result.first()


@router.get("/", response_model=CartSchema)
async def get_cart(db: AsyncSessionDep, current_user: CurrentUserDep) -> CartSchema:
    """Эндпоинт, который отвечает за получение данных корзины пользователя."""

    result = await db.scalars(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(CartItemModel.user_id == current_user.id)
        .order_by(CartItemModel.id)
    )
    items: list[CartItemSchema] = [CartItemSchema.model_validate(item) for item in result.all()]

    total_quantity = sum(item.quantity for item in items)
    price_items = (
        Decimal(item.quantity)
        * (item.product.price if item.product.price is not None else Decimal("0"))
        for item in items
    )
    total_price_decimal = sum(price_items, Decimal("0.00"))

    return CartSchema(
        user_id=current_user.id,
        items=items,
        total_quantity=total_quantity,
        total_price=total_price_decimal,
    )


@router.post("/items", response_model=CartItemSchema, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    payload: CartItemCreate, db: AsyncSessionDep, current_user: CurrentUserDep
) -> CartItemSchema:
    """Эндпоинт отвечающий за добавление товара в корзину."""

    await _ensure_product_available(db, payload.product_id)
    cart_item = await _get_cart_item(db, current_user.id, payload.product_id)

    if cart_item:
        cart_item.quantity += payload.quantity
    else:
        cart_item = CartItemModel(
            user_id=current_user.id,
            product_id=payload.product_id,
            quantity=payload.quantity,
        )
        db.add(cart_item)

    await db.commit()
    await db.refresh(cart_item)
    updated_item = await _get_cart_item(db, current_user.id, payload.product_id)

    return CartItemSchema.model_validate(updated_item)


@router.put("/items/{product_id}", response_model=CartItemSchema)
async def update_cart_item(
    product_id: int, payload: CartItemUpdate, db: AsyncSessionDep, current_user: CurrentUserDep
) -> CartItemSchema:
    """Эндпоинт отвечающий за обновление количества товаров в корзине."""
    await _ensure_product_available(db, product_id)

    cart_item = await _get_cart_item(db, current_user.id, product_id)
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар в корзине не найден",
        )

    cart_item.quantity = payload.quantity
    await db.commit()
    await db.refresh(cart_item)
    updated_item = await _get_cart_item(db, current_user.id, product_id)

    return CartItemSchema.model_validate(updated_item)


@router.delete("/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_cart(
    product_id: int, db: AsyncSessionDep, current_user: CurrentUserDep
) -> Response:
    """Эндпоинт для удаления товара из корзины."""

    cart_item = await _get_cart_item(db, current_user.id, product_id)
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Товар в корзине не найден",
        )

    await db.delete(cart_item)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(db: AsyncSessionDep, current_user: CurrentUserDep) -> Response:
    """Эндпоинт для полной очистки корзины"""

    await db.execute(delete(CartItemModel).where(CartItemModel.user_id == current_user.id))
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
