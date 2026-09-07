from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Строка подключения для SQLite
DATABASE_URL = "sqlite:///ecommerce.db"

# Создаём Engine
engine = create_engine(DATABASE_URL, echo=True)

# Настраиваем фабрику сеансов
SessionLocal = sessionmaker(bind=engine)


from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "postgresql+asyncpg://ecommerce_user:admin12345@localhost:9911/ecommerce_db"

async_engine = create_async_engine(DATABASE_URL, echo=True)

async_session_maker = async_sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass
