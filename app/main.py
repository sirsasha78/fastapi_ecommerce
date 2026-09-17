from fastapi import FastAPI

from app.routers import cart, categories, orders, products, reviews, users

app = FastAPI(
    title="FastAPI Интернет-магазин",
    version="0.1.0",
)

app.include_router(categories.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(reviews.router)
app.include_router(cart.router)
app.include_router(orders.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Корневой маршрут, подтверждающий, что API работает."""

    return {"message": "Добро пожаловать в API интернет-магазина!"}
