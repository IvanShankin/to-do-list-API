from datetime import timedelta, datetime, timezone
import os
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select, update
from dotenv import load_dotenv
from typing import List

from app.data_base.data_base import get_db
from app.models.models import Project, Task
from app.schemas import TokenData
from app.models import User


load_dotenv()  # Загружает переменные из .env
# Настройки аутентификации
SECRET_KEY = os.getenv('SECRET_KEY')
ACCESS_TOKEN_EXPIRE_MINUTES = float(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# создание токена для пользователя
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.login == token_data.username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


def hash_password(password: str) -> str:
    """Преобразует пароль в хеш
    :return: хэш пароля"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, совпадает ли пароль с хешем
    :param plain_password: простой пароль (qwerty)
    :param hashed_password: хэш пароля (gfdjkjvzvxccxa)
    :return:
    """
    return pwd_context.verify(plain_password, hashed_password)

def ensure_utc(dt: datetime) -> datetime:
    """
    :param dt: дата и время в любой временной зоне
    :return: дата и время в UTC
    """
    return dt.astimezone(timezone.utc)  # преобразуем в UTC

async def check_overdue_projects(user_id: int,
        projects_id: list[int],
        db: AsyncSession = Depends(get_db)
)->List[Project]:
    """
    обновляет устаревшие проекты в БД
    :param user_id: id пользователя
    :param projects_id: список из id проектов которые необходимо проверить
    :param db: подключение к БД (его передавать не обязательно)
    :return обновлённый список проектов:
    """
    if not projects_id:
        return []

    now = datetime.now(timezone.utc)

    # обновляем данные в БД
    await db.execute(
        update(Project)
        .where(
            (Project.user_id == user_id) &
            (Project.project_id.in_(projects_id)) &
            (Project.desired_completion_date < now) &
            (Project.actual_completion_date.is_(None)) &
            (Project.status_id != 2)
        ).values(status_id=2)) # Установление статуса - просрочен. Обновлять последнее использование не надо!

    #Получаем обновлённые проекты
    result = await db.execute(
        select(Project)
        .where(Project.project_id.in_(projects_id))
        .options(joinedload(Project.status))  # Загружаем связанный статус
    )
    await db.commit()
    new_projects = result.scalars().all()

    return new_projects


async def check_overdue_tasks(user_id: int,
        task_id: list[int],
        db: AsyncSession = Depends(get_db)
)->List[Task]:
    """
    обновляет устаревшие проекты в БД
    :param user_id: id пользователя
    :param task_id: список из id задач которые необходимо проверить
    :param db: подключение к БД (его передавать не обязательно)
    :return обновлённый список задач:
    """
    if not task_id:
        return []

    now = datetime.now(timezone.utc)

    # обновляем данные в БД
    await db.execute(
        update(Task)
        .where(
            (Task.user_id == user_id) &
            (Task.task_id.in_(task_id)) &
            (Task.desired_completion_date < now) &
            (Task.actual_completion_date.is_(None)) &
            (Task.status_id != 2)
        ).values(status_id=2)) # Установление статуса - просрочен. Обновлять последнее использование не надо!

    #Получаем обновлённые проекты
    result = await db.execute(
        select(Task)
        .where(Task.task_id.in_(task_id))
        .options(joinedload(Task.status))  # Загружаем связанный статус
    )
    await db.commit()
    new_task = result.scalars().all()

    return new_task
