from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import CurrentUserDep
from app.db_depends import AsyncSessionDep
from app.models.cart_items import CartItem as CartItemModel
from app.models.orders import Order as OrderModel
from app.models.orders import OrderItem as OrderItemModel
from app.schemas import Order as OrderSchema
from app.schemas import OrderList

router = APIRouter(
    prefix="/orders",
    tags=["orders-v1"],
)


async def _load_order_with_items(db: AsyncSession, order_id: int) -> OrderModel | None:
    """Вспомогательная функция для загрузки заказа с товарами"""

    result = await db.scalars(
        select(OrderModel)
        .options(selectinload(OrderModel.items).selectinload(OrderItemModel.product))
        .where(OrderModel.id == order_id)
    )

    return result.first()


@router.get("/", response_model=OrderList)
async def list_orders(
    db: AsyncSessionDep,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> OrderList:
    """Возвращает заказы текущего пользователя с простой пагинацией."""

    total = await db.scalar(
        select(func.count(OrderModel.id)).where(OrderModel.user_id == current_user.id)
    )
    result = await db.scalars(
        select(OrderModel)
        .options(selectinload(OrderModel.items).selectinload(OrderItemModel.product))
        .where(OrderModel.user_id == current_user.id)
        .order_by(OrderModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    orders: list[OrderSchema] = [OrderSchema.model_validate(item) for item in result.all()]

    return OrderList(
        items=orders,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("/checkout", response_model=OrderSchema, status_code=status.HTTP_201_CREATED)
async def checkout_order(db: AsyncSessionDep, current_user: CurrentUserDep) -> OrderSchema:
    """
    Создаёт заказ на основе текущей корзины пользователя.
    Сохраняет позиции заказа, вычитает остатки и очищает корзину.
    """

    cart_result = await db.scalars(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(CartItemModel.user_id == current_user.id)
        .order_by(CartItemModel.id)
    )
    cart_items = cart_result.all()
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Корзина пуста",
        )

    order = OrderModel(user_id=current_user.id)
    total_amount = Decimal("0")

    for cart_item in cart_items:
        product = cart_item.product
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Товар {cart_item.product_id} недоступен",
            )
        if product.stock < cart_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недостаточно запасов для товара {product.name}",
            )

        unit_price = product.price
        total_price = unit_price * cart_item.quantity
        total_amount += total_price

        order_item = OrderItemModel(
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            unit_price=unit_price,
            total_price=total_price,
        )

        order.items.append(order_item)
        product.stock -= cart_item.quantity

    order.total_amount = total_amount
    db.add(order)

    await db.execute(delete(CartItemModel).where(CartItemModel.user_id == current_user.id))
    await db.commit()

    created_order = await _load_order_with_items(db, order.id)
    if not created_order:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось загрузить созданный заказ",
        )

    return OrderSchema.model_validate(created_order)


@router.get("/{order_id}", response_model=OrderSchema)
async def get_order(
    order_id: int, db: AsyncSessionDep, current_user: CurrentUserDep
) -> OrderSchema:
    """Возвращает детальную информацию по заказу, если он принадлежит пользователю."""

    order = await _load_order_with_items(db, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заказ не найден",
        )

    return OrderSchema.model_validate(order)
