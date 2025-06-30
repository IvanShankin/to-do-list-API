import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()  # Загружает переменные из .env
HOST = os.getenv('HOST')
USER = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# postgresql+asyncpg это означает, что БД работает в асинхронном режиме
SQL_DB_URL = f'postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}/{DB_NAME}'

Base = declarative_base() # это подключение

engine_for_create = create_async_engine(SQL_DB_URL)

async def get_db()->AsyncSession:
    # это переменная для создания подключения
    engine = create_async_engine(SQL_DB_URL)

    # bind это какой движок необходимо использовать
    session_local = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )

    db = session_local()
    try:
        yield db
    finally:
        await db.close()


async def create_tables():
    """Асинхронная функция для создания таблиц в БД"""
    async with engine_for_create.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)