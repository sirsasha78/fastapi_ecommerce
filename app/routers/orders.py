from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.orders import Order as OrderModel
from app.models.orders import OrderItem as OrderItemModel

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)


async def _load_order_with_items(db: AsyncSession, order_id: int) -> OrderModel | None:
    """Вспомогательная функция для загрузки заказа с товарами"""

    result = await db.scalars(
        select(OrderModel)
        .options(selectinload(OrderModel.items).selectinload(OrderItemModel.product))
        .where(OrderModel.id == order_id)
    )

    return result.first()
