from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth import CurrentUserDep
from app.db_depends import AsyncSessionDep
from app.models.cart_items import CartItem as CartItemModel
from app.models.products import Product as ProductModel
from app.schemas import Cart as CartSchema
from app.schemas import CartItem as CartItemSchema

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
    """Эндпоинт, который отвечает за получение данных корзины пользователя"""

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
