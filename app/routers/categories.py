from fastapi import APIRouter

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


@router.get("/")
async def get_all_categories() -> dict[str, str]:
    """Возвращает список всех категорий товаров."""

    return {"message": "Список всех категорий (заглушка)"}


@router.post("/")
async def create_category() -> dict[str, str]:
    """Создаёт новую категорию."""

    return {"message": "Категория создана (заглушка)"}


@router.put("/{category_id}")
async def update_category(category_id: int) -> dict[str, str]:
    """Обновляет категорию по её ID."""

    return {"message": f"Категория с ID {category_id} обновлена (заглушка)"}


@router.delete("/{category_id}")
async def delete_category(category_id: int) -> dict[str, str]:
    """Удаляет категорию по её ID."""

    return {"message": f"Категория с ID {category_id} удалена (заглушка)"}
