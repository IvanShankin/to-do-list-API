import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text, select
from dotenv import load_dotenv

from app.data_base.base import Base
from app.models import Status

load_dotenv()  # Загружает переменные из .env
HOST = os.getenv('HOST')
USER = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# URL для подключения к серверу PostgreSQL без указания конкретной базы данных
POSTGRES_SERVER_URL = f'postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}/postgres'
# postgresql+asyncpg это означает, что БД работает в асинхронном режиме
SQL_DB_URL = f'postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}/{DB_NAME}'

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

async def create_database():
    """Создает базу данных (если она не существует) и все таблицы в ней."""
    # Сначала подключаемся к серверу PostgreSQL без указания конкретной базы
    engine = create_async_engine(POSTGRES_SERVER_URL, isolation_level="AUTOCOMMIT")
    print('\n\n\n\n\n\n\n\n' + DB_NAME + '\n\n\n\n\n\n\n\n')
    try:
        # Проверяем существование базы данных и создаем если ее нет
        async with engine.connect() as conn:
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
            )
            database_exists = result.scalar() == 1

            if not database_exists:
                logging.info(f"Creating database {DB_NAME}...")
                await conn.execute(text(f"CREATE DATABASE {DB_NAME}"))
                logging.info(f"Database {DB_NAME} created successfully")
            else:
                logging.info(f"Database {DB_NAME} already exists")
    except Exception as e:
        logging.error(f"Error checking/creating database: {e}")
        raise
    finally:
        await engine.dispose()

    # Теперь создаем таблицы в целевой базе данных
    engine = create_async_engine(SQL_DB_URL)
    try:
        async with engine.begin() as conn:
            logging.info("Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
            logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")
        raise
    finally:
        await engine.dispose()

    engine = create_async_engine(SQL_DB_URL)
    async with AsyncSession(engine) as session:
        for status_name in ['in_progress', 'completed', 'overdue', 'deleted']:
            await create_status_if_not_exists(session, status_name)
        await session.commit()
    await engine.dispose()


async def create_status_if_not_exists(db: AsyncSession, status_name: str):
    """
    Создаёт запись статуса, если она не существует.

    :param db: Асинхронная сессия БД
    :param status_name: Название статуса
    :return: Объект статуса (существующий или новый)
    """
    # Проверяем существование статуса
    result = await db.execute(
        select(Status).where(Status.name == status_name)
    )
    status = result.scalar_one_or_none()

    if status is None:
        # Создаём новый статус
        status = Status(name=status_name)
        db.add(status)
        await db.commit()
        await db.refresh(status)
        logging.info(f"Created new status: {status_name}")
    else:
        logging.info(f"Status already exists: {status_name}")

    return status