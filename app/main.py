from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import cart, categories, orders, products, reviews, users

app = FastAPI(
    title="FastAPI Интернет-магазин",
    version="0.1.0",
)

app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(categories.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(reviews.router, prefix="/api/v1")
app.include_router(cart.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Корневой маршрут, подтверждающий, что API работает."""

    return {"message": "Добро пожаловать в API интернет-магазина!"}
