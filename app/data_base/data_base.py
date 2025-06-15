from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import HOST,USER, PASSWORD, DB_NAME

# postgresql+asyncpg это означает, что БД работает в асинхронном режиме
SQL_DB_URL = f'postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}/{DB_NAME}'

# это переменная для создания подключения
engine = create_async_engine(SQL_DB_URL)

# bind это какой движок необходимо использовать
session_local = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base() # это подключение


