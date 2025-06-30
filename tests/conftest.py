import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, cast, func, Boolean
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from app.dependencies import hash_password
from app.models.models import User, Project, Status, Task
from app.dependencies import create_access_token
from app.data_base.data_base import get_db
from app.dependencies import ensure_utc

import pytest
import pytest_asyncio  # Используем специальный декоратор

load_dotenv()  # Загружает переменные из .env
ACCESS_TOKEN_EXPIRE_MINUTES = float(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
MODE = os.getenv('MODE')

@pytest_asyncio.fixture
async def db_session()->AsyncSession:
    """Соединение с БД"""
    db_gen = get_db()
    session = await db_gen.__anext__()
    try:
        yield session
    finally:
        await session.close()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def clearing_db(db_session: AsyncSession):
    """Очищает базу данных после каждого теста"""

    await db_session.execute(delete(Task))
    await db_session.execute(delete(Project))
    await db_session.execute(delete(User))
    await db_session.commit()


@pytest_asyncio.fixture(scope="function") # будет вызываться для каждого метода
async def create_user(db_session)-> dict:
    """
    Создает тестового пользователя и возвращает данные о нём
    :return: dict{'user_id', 'user_name', 'password', 'hashed_password', 'email', 'access_token'}
    """
    db = db_session

    hashed_password = hash_password("first_password_test")
    new_user = User(
        login="first_user_test",
        password=hashed_password,
        email="first_email_test@gmail.com",
        created_date=datetime.now(),
        last_login=datetime.now()
    )

    db.add(new_user)
    await db.commit()
    await db_session.refresh(new_user)

    # Создаем токен для этого пользователя
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.login},
        expires_delta=access_token_expires
    )

    return {'user_id': new_user.user_id,
            'user_name': new_user.login,
            'password': 'first_password_test',
            'hashed_password': new_user.password,
            'email': new_user.email,
            'access_token': access_token,
            }

@pytest_asyncio.fixture(scope='function')
async def create_project(db_session, create_user)->dict:
    """
    Создаёт проект и пользователя
    :return: dict{'project_id', 'status_id', 'position_index', 'title', 'description', 'created_date',
    'desired_completion_date', 'updated_date', 'data_user': данные которые возвращаются из фикстуры  create_user}
    """

    query = select(func.max(Project.position_index)).where(cast(
        (Project.user_id == create_user['user_id']) &
        (Project.status_id != 3), Boolean
    ))

    result = await db_session.execute(query)
    max_position = result.scalar_one_or_none()
    if not max_position is None:
        new_position = max_position + 1
    else:  # если ранее в БД не было задач у этого проекта
        new_position = 0

    status_result = await db_session.execute(select(Status).where(cast(Status.status_id == 0, Boolean)))
    status_from_db = status_result.scalar_one_or_none()

    created_date = datetime.now(timezone.utc)
    more_date = datetime.now(timezone.utc) + timedelta(days=5)

    new_project = Project(user_id=create_user['user_id'],
                          status_id=status_from_db.status_id,
                          position_index=new_position,
                          title='test_title',
                          description='test_description',
                          created_date=created_date,
                          desired_completion_date=more_date,
                          updated_date=created_date
                          )
    db_session.add(new_project)
    await db_session.commit()
    await db_session.refresh(new_project)
    new_project.status = status_from_db

    return {'project_id': new_project.project_id,
            'status_id': status_from_db.status_id,
            'position_index': new_position,
            'title': new_project.title,
            'description': new_project.description,
            'created_date': created_date,
            'desired_completion_date': more_date,
            'updated_date': created_date,
            'data_user': create_user
    }

@pytest_asyncio.fixture(scope='function')
async def create_task(db_session, create_user, create_project)->dict:
    result = await db_session.execute(select(func.max(Task.position_index)).where(cast(
        (Task.user_id == create_user['user_id']) &
        (Task.status_id != 3) &  # если не удалён
        (Task.project_id == create_project['project_id']),  # ищем по tasks который так же находятся в этом проекте
        Boolean
    )))

    max_position = result.scalar_one_or_none()
    if not max_position is None:
        new_position = max_position + 1
    else:  # если ранее в БД не было задач у этого проекта
        new_position = 0

    status_result = await db_session.execute(select(Status).where(cast(Status.status_id == 0, Boolean)))
    status_from_db = status_result.scalar_one_or_none()

    created_date = datetime.now(timezone.utc)
    more_date = datetime.now(timezone.utc) + timedelta(days=5)

    new_task = Task(user_id=create_user['user_id'],
                    project_id=create_project['project_id'],
                    status_id=status_from_db.status_id,
                    position_index=new_position,
                    title=create_project['title'],
                    description=create_project['description'],
                    created_date=created_date,
                    desired_completion_date=more_date,
                    updated_date=created_date
                    )
    db_session.add(new_task)
    await db_session.commit()
    await db_session.refresh(new_task)
    new_task.status = status_from_db

    return {'task_id': new_task.task_id,
            'project_id': new_task.project_id,
            'status_id': new_task.status_id,
            'position_index': new_task.position_index,
            'priority': new_task.priority,
            'title': new_task.title,
            'description': new_task.description,
            'created_date': created_date,
            'desired_completion_date': more_date,
            'updated_date': created_date,
            'data_user': create_user,
    }
