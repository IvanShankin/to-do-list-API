from fastapi import APIRouter, Depends, HTTPException, status, Query

from sqlalchemy import select, cast, Boolean
from sqlalchemy.ext.asyncio import AsyncSession

from typing import List, Optional

from app.dependencies import get_db, get_current_user, check_overdue_projects, check_overdue_tasks
from app.models.models import User, Project, Task
from app.schemas.response import ProjectResponse, TaskResponse, UserResponse

router = APIRouter()


@router.get("/users/me/", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get('/get_project/', response_model= List[ProjectResponse])
async def get_project(
        project_id: Optional[int] = Query(None, description="ID проекта"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if project_id is None: # если необходимо вернуть все проекты
        result = await db.execute(select(Project).where(cast(
            (Project.user_id == current_user.user_id)
            & (Project.status_id != 3), Boolean
        )))
        projects = result.scalars().all()
    else:
        result = await db.execute(select(Project).where(cast(
            (Project.user_id == current_user.user_id) &
            (Project.project_id == project_id), Boolean
        )))
        project = result.scalars().one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Проект с ID {project_id} не найден"
            )

        if project.status_id == 3:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Проект с ID {project_id} удалён"
        )
        projects = [project]  # Заворачиваем в список для соответствия response_model

    # Проверка просроченности
    update_projects = await check_overdue_projects(current_user.user_id, [p.project_id for p in projects], db)

    return update_projects

@router.get('/get_task/', response_model=List[TaskResponse])
async def get_task(
        project_id: Optional[int] = Query(None, description="ID проекта"),
        task_id: Optional[int] = Query(None, description="ID задачи"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    if (not task_id is None) and (not project_id is None): # если передали два параметра
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать либо project_id, либо task_id"
        )
    elif not task_id is None: # если передали только task_id -> вернём эту задачу
        result = await db.execute(select(Task).where(cast(
            (Task.user_id == current_user.user_id) &
            (Task.task_id == task_id),Boolean
        )))
        task = result.scalars().one_or_none()
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Задача с ID {task_id} не найден"
            )

        if task.status_id == 3:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задача с ID {task_id} удалён"
        )
        tasks = [task]  # Заворачиваем в список для соответствия response_model
    elif not project_id is None: # если передали только project_id -> вернём эту все задачи в этом проекте
        result = await db.execute(select(Task).where(cast(
            (Task.user_id == current_user.user_id) &
            (Task.project_id == project_id) &
            (Task.status_id != 3), Boolean # если не удален
        )))
        tasks = result.scalars().all()
    else: # ничего не передали -> необходимо вернуть все задачи
        result = await db.execute(select(Task).where(cast(
            Task.user_id == current_user.user_id, Boolean
        )))
        tasks = result.scalars().all()

    # Проверка просроченности
    update_tasks = await check_overdue_tasks(current_user.user_id, [p.task_id for p in tasks], db)

    return update_tasks

