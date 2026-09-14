from fastapi import APIRouter, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.sql import func

from app.auth import CurrentBuyerDep
from app.db_depends import AsyncSessionDep
from app.models import Product as ProductModel
from app.models import Review as ReviewModel
from app.schemas import ReviewCreate, ReviewRead

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)


async def update_product_rating(db: AsyncSessionDep, product_id: int) -> None:
    """Пересчитывает средний рейтинг товара на основе активных отзывов."""

    result = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active.is_(True),
        )
    )
    avg_rating = result.scalar() or 0.0
    product = await db.get(ProductModel, product_id)
    if product is None:
        return

    product.rating = avg_rating
    await db.commit()


@router.get("/", response_model=list[ReviewRead])
async def get_all_reviews(db: AsyncSessionDep) -> list[ReviewModel]:
    """Возвращает список всех отзывов."""

    result = await db.scalars(
        select(ReviewModel)
        .where(ReviewModel.is_active.is_(True))
        .order_by(desc(ReviewModel.comment_date))
    )
    reviews = result.all()

    return list(reviews)


@router.post("/", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def create_review(
    current_user: CurrentBuyerDep, db: AsyncSessionDep, review: ReviewCreate
) -> ReviewModel:
    """Создаёт новый отзыв, привязанный к текущему покупателю (только для 'buyer')."""
    result = await db.scalars(
        select(ProductModel).where(
            ProductModel.id == review.product_id, ProductModel.is_active.is_(True)
        )
    )
    product = result.first()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Продукт не найден или неактивен",
        )

    result_review = await db.scalars(
        select(ReviewModel).where(
            ReviewModel.user_id == current_user.id,
            ReviewModel.product_id == review.product_id,
            ReviewModel.is_active.is_(True),
        )
    )
    exists = result_review.first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Покупатель может оставить только один отзыв на товар",
        )

    db_review = ReviewModel(**review.model_dump(), user_id=current_user.id)
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    await update_product_rating(db, review.product_id)

    return db_review
