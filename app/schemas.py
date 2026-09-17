from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import Form
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CategoryCreate(BaseModel):
    """
    Модель для создания и обновления категории.
    Используется в POST и PUT запросах.
    """

    name: Annotated[
        str, Field(min_length=3, max_length=50, description="Название категории (3-50 символов)")
    ]
    parent_id: Annotated[
        int | None, Field(description="ID родительской категории, если есть")
    ] = None


class Category(CategoryCreate):
    """
    Модель для ответа с данными категории.
    Используется в GET-запросах.
    """

    id: Annotated[int, Field(description="Уникальный идентификатор категории")]
    is_active: Annotated[bool, Field(description="Активность категории")]
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """
    Модель для создания и обновления товара.
    Используется в POST и PUT запросах.
    """

    name: Annotated[
        str, Field(min_length=3, max_length=100, description="Название товара (3-100 символов)")
    ]
    description: Annotated[
        str | None, Field(max_length=500, description="Описание товара (до 500 символов)")
    ] = None
    price: Annotated[Decimal, Field(gt=0, decimal_places=2, description="Цена товара (больше 0)")]
    stock: Annotated[int, Field(ge=0, description="Количество товара на складе (0 или больше)")]
    category_id: Annotated[int, Field(description="ID категории, к которой относится товар")]

    @classmethod
    def as_form(
        cls,
        name: Annotated[str, Form(...)],
        price: Annotated[Decimal, Form(...)],
        stock: Annotated[int, Form(...)],
        category_id: Annotated[int, Form(...)],
        description: Annotated[str | None, Form()] = None,
    ) -> "ProductCreate":
        return cls(
            name=name,
            description=description,
            price=price,
            stock=stock,
            category_id=category_id,
        )


class Product(ProductCreate):
    """
    Модель для ответа с данными товара.
    Используется в GET-запросах.
    """

    id: Annotated[int, Field(description="Уникальный идентификатор товара")]
    is_active: Annotated[bool, Field(description="Активность товара")]
    rating: Annotated[float, Field(description="Рэйтинг товара")]
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Модель для создания и обновления пользователя."""

    email: Annotated[EmailStr, Field(description="Email пользователя")]
    password: Annotated[str, Field(min_length=8, description="Пароль (минимум 8 символов)")]
    role: Annotated[
        str,
        Field(
            default="buyer", pattern="^(buyer|seller)$", description="Роль: 'buyer' или 'seller'"
        ),
    ]


class User(BaseModel):
    """Модель для ответа с данными пользователя."""

    id: int
    email: EmailStr
    is_active: bool
    role: str
    model_config = ConfigDict(from_attributes=True)


class RefreshTokenRequest(BaseModel):
    """Модель для обновления refresh-токена"""

    refresh_token: str


class ReviewCreate(BaseModel):
    """Модель для создания отзыва."""

    product_id: Annotated[int, Field(description="ID товара, к которому относится отзыв")]
    comment: Annotated[
        str | None, Field(default=None, max_length=4000, description="Текст отзыва")
    ]
    grade: Annotated[int, Field(ge=1, le=5, description="Оценка товара от 1 до 5")]


class ReviewRead(ReviewCreate):
    """Модель для ответа с данными отзыва."""

    model_config = ConfigDict(from_attributes=True)
    id: Annotated[int, Field(description="Уникальный идентификатор отзыва")]
    user_id: Annotated[int, Field(description="ID пользователя, который оставил отзыв")]
    comment_date: Annotated[datetime, Field(description="Дата и время создания отзыва")]
    is_active: Annotated[bool, Field(description="Активность отзыва")]


class ProductList(BaseModel):
    """Список пагинации для товаров."""

    items: Annotated[list[Product], Field(description="Товары для текущей страницы")]
    total: Annotated[int, Field(ge=0, description="Общее количество товаров")]
    page: Annotated[int, Field(ge=1, description="Номер текущей страницы")]
    page_size: Annotated[int, Field(ge=1, description="Количество элементов на странице")]
    model_config = ConfigDict(from_attributes=True)


class CartItemBase(BaseModel):
    """Базовая модель для корзины товаров."""

    product_id: Annotated[int, Field(description="ID товара")]
    quantity: Annotated[int, Field(ge=1, description="Количество товара")]


class CartItemCreate(CartItemBase):
    """Модель для добавления нового товара в корзину."""

    pass


class CartItemUpdate(BaseModel):
    """Модель для обновления количества товара в корзине."""

    quantity: Annotated[int, Field(ge=1, description="Новое количество товара")]


class CartItem(BaseModel):
    """Товар в корзине с данными продукта."""

    id: Annotated[int, Field(description="ID позиции корзины")]
    quantity: Annotated[int, Field(ge=1, description="Количество товара")]
    product: Annotated[Product, Field(description="Информация о товаре")]
    model_config = ConfigDict(from_attributes=True)


class Cart(BaseModel):
    """Полная информация о корзине пользователя."""

    user_id: Annotated[int, Field(description="ID пользователя")]
    items: Annotated[
        list[CartItem], Field(default_factory=list, description="Содержимое корзины")
    ]
    total_quantity: Annotated[int, Field(ge=0, description="Общее количество товаров")]
    total_price: Annotated[Decimal, Field(ge=0, description="Общая стоимость товаров")]
    model_config = ConfigDict(from_attributes=True)


class OrderItem(BaseModel):
    """МодельБ которая, описывает одну строку заказа"""

    id: Annotated[int, Field(description="ID позиции заказа")]
    product_id: Annotated[int, Field(description="ID товара")]
    quantity: Annotated[int, Field(ge=1, description="Количество")]
    unit_price: Annotated[Decimal, Field(ge=0, description="Цена за единицу на момент покупки")]
    total_price: Annotated[Decimal, Field(ge=0, description="Сумма по позиции")]
    product: Annotated[
        Product | None, Field(default=None, description="Полная информация о товаре")
    ]

    model_config = ConfigDict(from_attributes=True)


class Order(BaseModel):
    """Модель для полного представления заказа"""

    id: Annotated[int, Field(description="ID заказа")]
    user_id: Annotated[int, Field(description="ID пользователя")]
    status: Annotated[str, Field(description="Текущий статус заказа")]
    total_amount: Annotated[Decimal, Field(ge=0, description="Общая стоимость")]
    created_at: Annotated[datetime, Field(description="Когда заказ был создан")]
    updated_at: Annotated[datetime, Field(description="Когда последний раз обновлялся")]
    items: Annotated[list[OrderItem], Field(default_factory=list, description="Список позиций")]

    model_config = ConfigDict(from_attributes=True)


class OrderList(BaseModel):
    """Модель для пагинированных списков заказов"""

    items: Annotated[list[Order], Field(description="Заказы на текущей странице")]
    total: Annotated[int, Field(ge=0, description="Общее количество заказов")]
    page: Annotated[int, Field(ge=1, description="Текущая страница")]
    page_size: Annotated[int, Field(ge=1, description="Размер страницы")]

    model_config = ConfigDict(from_attributes=True)
