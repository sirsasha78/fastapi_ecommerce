from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Зависимость для получения сессии базы данных.
    Создаёт новую сессию для каждого запроса и закрывает её после обработки.
    """

    db: Session = SessionLocal()

    try:
        yield db
    finally:
        db.close()


SessionDep = Annotated[Session, Depends(get_db)]
