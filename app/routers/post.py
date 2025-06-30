from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update, func, cast, Boolean, delete
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends, HTTPException, status, APIRouter, Query
from fastapi.security import OAuth2PasswordRequestForm

from app.data_base.data_base import get_db
from app.dependencies import check_overdue_projects, check_overdue_tasks
from app.models.models import User, Project, Status, Task
from app.schemas.request import RefreshTokenRequest, ProjectCreate, TaskCreate, UserCreate, UpdateProject, UpdateTask
from app.schemas.response import TaskResponse, Token, ProjectResponse, UserResponse, DeleteProjectResponse, DeleteTaskResponse
from app.dependencies import (hash_password, verify_password, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES,
                              create_access_token, SECRET_KEY, ALGORITHM, ensure_utc, JWTError, jwt)

router = APIRouter()

@router.post("/new_user", response_model=UserResponse)
async def create_user(user: UserCreate,
                      db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(cast(User.login == user.login, Boolean)))
    db_user = result.scalar_one_or_none()
    if db_user:
        raise HTTPException(status_code=400, detail="Login already registered")

    # Проверка существующего email
    result = await db.execute(select(User).where(cast(User.email == user.email, Boolean)))
    db_user_email = result.scalar_one_or_none()
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Создание нового пользователя
    hashed_password = hash_password(user.password)
    db_user = User(
        login=user.login,
        password=hashed_password,
        email=user.email,
        created_date=datetime.now(),
        last_login=datetime.now()
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.post('/token', response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(),
                                 db: AsyncSession = Depends(get_db)):
    user = await db.execute(
        select(User).where(cast(User.login == form_data.username, Boolean)))
    db_user = user.scalar_one_or_none()

    if not db_user or not verify_password(form_data.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный user_name или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Обновляем время последнего входа
    db_user.last_login = datetime.now()
    await db.commit()

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# для обновления токена (со стороны клиента посылается старый токен)
@router.post('/refresh_token', response_model=Token)
async def refresh_token(request: RefreshTokenRequest,
                        db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        # Проверяем, что пользователь существует
        user = await db.execute(select(User).where(cast(User.login == username, Boolean)))
        user = user.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Генерируем новый Access Token
        new_access_token = create_access_token(data={"sub": username})
        return {"access_token": new_access_token, "token_type": "bearer"}

    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token expired or invalid")

@router.post("/create_project", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    query = select(func.max(Project.position_index)).where(cast((
        Project.user_id == current_user.user_id) & (Project.status_id != 3), Boolean
    ))
    result = await db.execute(query)
    max_position = result.scalar_one_or_none()
    if not max_position is None:
        new_position = max_position + 1
    else:  # если ранее в БД не было задач у этого проекта
        new_position = 0

    status_result = await db.execute(select(Status).where(cast(Status.status_id == 0, Boolean)))
    status_from_db = status_result.scalar_one_or_none()

    if project_data.desired_completion_date is None:
        dt_completion = None
    else:
        dt_completion = ensure_utc(project_data.desired_completion_date)

    new_project = Project(user_id=current_user.user_id,
                          status_id=status_from_db.status_id,
                          position_index=new_position,
                          title=project_data.title,
                          description=project_data.description,
                          created_date=datetime.now(timezone.utc),
                          desired_completion_date=dt_completion,
                          updated_date=datetime.now(timezone.utc))
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)
    new_project.status = status_from_db  # Устанавливаем уже загруженный статус через relationship. ЭТО ДЕЛАЕТСЯ ЧЕРЕЗ ПОЛЕ status
    return new_project

@router.post('/create_task', response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Проверяем существование проекта
    project = await db.get(Project, task_data.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Проект с ID {task_data.project_id} не найден"
        )

    result = await db.execute(select(func.max(Task.position_index)).where(cast(
        (Task.user_id == current_user.user_id) &
        (Task.status_id != 3) &                   # если не удалён
        (Task.project_id == task_data.project_id),# ищем по tasks который так же находятся в этом проекте
        Boolean
    )))

    max_position = result.scalar_one_or_none()
    if not max_position is None:
        new_position = max_position + 1
    else:  # если ранее в БД не было задач у этого проекта
        new_position = 0

    status_result = await db.execute(select(Status).where(cast(Status.status_id == 0, Boolean)))
    status_from_db = status_result.scalar_one_or_none()

    if task_data.desired_completion_date is None:
        dt_completion = None
    else:
        dt_completion = ensure_utc(task_data.desired_completion_date)

    new_task = Task(user_id=current_user.user_id,
                    project_id=task_data.project_id,
                    status_id=status_from_db.status_id,
                    position_index=new_position,
                    title=task_data.title,
                    description=task_data.description,
                    created_date=datetime.now(timezone.utc),
                    desired_completion_date=dt_completion,
                    updated_date=datetime.now(timezone.utc))
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    new_task.status = status_from_db
    return new_task

@router.post('/update_project', response_model=ProjectResponse)
async def update_project(
    project_data: UpdateProject,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = await db.execute(select(Project).where(cast(
        (Project.status_id != 3) &    # если не удалён
        (Project.user_id == current_user.user_id) &
        (Project.project_id == project_data.project_id), Boolean
    )))
    project = query.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Проект с ID {project_data.project_id} не найден"
        )

    if project_data.position_index is not None:
        query = await db.execute(select(func.max(Project.position_index)).where(cast(
            (Project.user_id == current_user.user_id) &
            (Project.status_id != 3), Boolean
        ))) or 0    # будет 0 если проектов нет (такого не должно произойти )
        max_index = query.scalar_one_or_none()

        if project_data.position_index > max_index:
            project_data.position_index = max_index

        old_index = project.position_index
        new_index = project_data.position_index

        if new_index != old_index:
            # Сдвигаем проекты между старым и новым индексом
            if new_index > old_index:
                # Двигаем ВСЕ проекты между старым и новым индексом ВНИЗ на 1
                await db.execute(
                    update(Project)
                    .where(
                        (Project.user_id == current_user.user_id) &
                        (Project.status_id != 3) &              # если не удалён
                        (Project.position_index > old_index) &  # > old_index (исключаем сам элемент)
                        (Project.position_index <= new_index)   # <= new_index (включаем новую позицию)
                    )
                    .values(position_index=Project.position_index - 1) # Сдвиг вниз
                )
            else:
                # Двигаем ВСЕ проекты между новым и старым индексом ВВЕРХ на 1
                await db.execute(
                    update(Project)
                    .where(
                        (Project.user_id == current_user.user_id) &
                        (Project.status_id != 3) &              # если не удалён
                        (Project.position_index >= new_index) & # >= new_index (включаем новую позицию)
                        (Project.position_index < old_index)    # < old_index (исключаем сам элемент)
                    )
                    .values(position_index=Project.position_index + 1) # Сдвиг вверх
                )

    # Обновляем только переданные поля
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items(): # получаем словарь из переданных данных
        if field != 'project_id' and hasattr(project, field): # войдём если в БД есть такой столбец как ключ у field
            setattr(project, field, value) # Устанавливаем новое значение для атрибута объекта

    # Обновляем дату изменения
    project.updated_date = datetime.now(timezone.utc)

    if project.desired_completion_date and project.desired_completion_date < datetime.now(timezone.utc):
        project.status_id = 2  # Просрочен

    if project.actual_completion_date:
        project.status_id = 1 # Завершен

    await db.commit()
    await db.refresh(project)

    status_result = await db.execute(select(Status).where(cast(
        Status.status_id == project.status_id, Boolean
    )))
    status_from_db = status_result.scalar_one_or_none()
    project.status = status_from_db
    return project


@router.post('/update_task', response_model=TaskResponse)
async def update_task(
    task_data: UpdateTask,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = await db.execute(select(Task).where(cast(
        (Task.status_id != 3) &    # если не удалён
        (Task.user_id == current_user.user_id) &
        (Task.task_id == task_data.task_id), Boolean
    )))
    task = query.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задача с ID {task_data.task_id} не найден"
        )

    if task_data.position_index is not None:
        query = await db.execute(select(func.max(Task.position_index)).where(cast(
            (Task.user_id == current_user.user_id) &
            (Task.status_id != 3), Boolean
        ))) or 0    # будет 0 если задач нет (такого не должно произойти )
        max_index = query.scalar_one_or_none()

        if task_data.position_index > max_index:
            task_data.position_index = max_index

        old_index = task.position_index
        new_index = task_data.position_index

        if new_index != old_index:
            # Сдвигаем задачи между старым и новым индексом
            if new_index > old_index:
                # Двигаем ВСЕ задачи между старым и новым индексом ВНИЗ на 1
                await db.execute(
                    update(Task)
                    .where(
                        (Task.user_id == current_user.user_id) &
                        (Task.status_id != 3) &              # если не удалён
                        (Task.position_index > old_index) &  # > old_index (исключаем сам элемент)
                        (Task.position_index <= new_index)   # <= new_index (включаем новую позицию)
                    ).values(position_index=Task.position_index - 1) # Сдвиг вниз
                )
            else:
                # Двигаем ВСЕ задачи между новым и старым индексом ВВЕРХ на 1
                await db.execute(
                    update(Task)
                    .where(
                        (Task.user_id == current_user.user_id) &
                        (Task.status_id != 3) &              # если не удалён
                        (Task.position_index >= new_index) & # >= new_index (включаем новую позицию)
                        (Task.position_index < old_index)    # < old_index (исключаем сам элемент)
                    ).values(position_index=Task.position_index + 1) # Сдвиг вверх
                )

    # Обновляем только переданные поля
    update_data = task_data.model_dump(exclude_unset=True)
    for field, value in update_data.items(): # получаем словарь из переданных данных
        if field != 'task_id' and hasattr(task, field): # войдём если в БД есть такой столбец как ключ у field
            setattr(task, field, value) # Устанавливаем новое значение для атрибута объекта

    # Обновляем дату изменения
    task.updated_date = datetime.now(timezone.utc)

    if task.desired_completion_date and task.desired_completion_date < datetime.now(timezone.utc):
        task.status_id = 2  # Просрочен

    if task.actual_completion_date:
        task.status_id = 1 # Завершен

    await db.commit()
    await db.refresh(task)

    status_result = await db.execute(select(Status).where(cast(
        Status.status_id == task.status_id, Boolean
    )))
    status_from_db = status_result.scalar_one_or_none()
    task.status = status_from_db
    return task


@router.post('/delete_project', response_model=DeleteProjectResponse)
async def delete_project(
        project_id: int = Query(..., description="ID проекта"),
        complete_remove: bool = Query(False, description="Флаг полного удаления с БД"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Project).where(cast(
        (Project.user_id == current_user.user_id) &
        (Project.project_id == project_id), Boolean
    )))

    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Проект с ID {project_id} не найден"
        )

    old_position_index = project.position_index
    old_status_id = project.status_id

    if complete_remove: # если необходимо полностью удалить (удаляем с БД)
        # удаление всех задач у этого проекта
        task_delete = await db.execute(delete(Task).where(cast((Task.project_id == project_id), Boolean)))
        # удаление проекта
        await db.execute(delete(Project).where(cast((Project.project_id == project_id), Boolean)))
        msg = "Проект и все задачи полностью удалены"
    else: # Архивация
        task_update = await db.execute(update(Task).where(cast(
            (Task.project_id == project_id), Boolean)
        ).values(status_id=3, position_index= -1)  # статус = удалённый
        )  # помечаем в БД, что все задач у этого проекта удалены

        await db.execute(update(Project).where(cast(
            (Project.project_id == project_id), Boolean)
        ).values(status_id=3, position_index= -1) # статус = удалённый
        )  # помечаем в БД, что проект удалён
        msg = "Проект и задачи перемещены в архив"

    # Обновление позиций только для активных проектов
    if old_status_id != 3: # если не удалён (иначе нет необходимости двигать индексы)
        await db.execute(update(Project).where(cast(
            (Project.user_id == current_user.user_id) &
            (Project.position_index > old_position_index), Boolean # проверять на удалённый статус не надо, ибо проекты с ним имеют позицию -1
        )).values(position_index= Project.position_index - 1)
        )  # каждое значение в бд которое идёт после удалённого индекса, сдвигаем к нулю на одно значение (-1)

    await db.commit()
    new_delete_project = DeleteProjectResponse(
        message=msg,
        project_id=project_id,
        deleted_at=datetime.now(timezone.utc),
        affected_tasks_count= task_delete.rowcount if complete_remove else task_update.rowcount
    )
    return new_delete_project

@router.post('/delete_task', response_model=DeleteTaskResponse)
async def delete_task(
        task_id: int = Query(..., description="ID задачи"),
        complete_remove: bool = Query(False, description="Флаг полного удаления с БД"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(cast(
        (Task.user_id == current_user.user_id) &
        (Task.task_id == task_id), Boolean
    )))

    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задача с ID {task_id} не найдена"
        )

    old_position_index = task.position_index
    old_status_id = task.status_id
    old_project_id = task.project_id

    if complete_remove:  # если необходимо полностью удалить (удаляем с БД)
        await db.execute(delete(Task).where(cast((Task.task_id == task_id), Boolean)))
        msg = "Задача полностью удалена"
    else:  # Архивация
        await db.execute(update(Task).where(cast(
            (Task.task_id == task_id), Boolean)
        ).values(status_id=3, position_index=-1)  # статус = удалённый
        )  # помечаем в БД, что задача удалена
        msg = "Задача перемещена в архив"

    # Обновление позиций только для активных задач
    if old_status_id != 3:  # если не удалён (иначе нет необходимости двигать индексы)
        await db.execute(update(Task).where(cast(
            (Task.user_id == current_user.user_id) &
            (Task.project_id == old_project_id) &
            (Task.position_index > old_position_index), Boolean # проверять на удалённый статус не надо, ибо задачи с ним имеют позицию -1
        )).values(position_index=Task.position_index - 1)
        )  # каждое значение в бд которое идёт после удалённого индекса, сдвигаем к нулю на одно значение (-1)

    await db.commit()
    new_delete_task = DeleteTaskResponse(
        message=msg,
        task_id=task_id,
        project_id=old_project_id,
        deleted_at=datetime.now(timezone.utc),
        affected_tasks_count=1
    )
    return new_delete_task


@router.post('/recover_project', response_model=ProjectResponse)
async def recover_project(
        project_id: int = Query(..., description="ID проекта"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Project).where(cast(
        (Project.project_id == project_id) &
        (Project.user_id == current_user.user_id),Boolean
    )))

    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Проект с ID {project_id} не найдена"
        )

    if project.status_id != 3:  # если не является удалённым
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Проект с ID {project_id} не является удалённым (текущий статус {project.status_id})"
        )

    # Находим максимальный position_index среди активных проектов пользователя
    max_pos_result = await db.execute(
        select(func.max(Project.position_index)).where(cast(
            (Project.user_id == current_user.user_id) &
            (Project.status_id != 3), Boolean  # Только не удалённые проекты
        ))
    )
    max_position = max_pos_result.scalar_one_or_none() or 0

    # Обновляем проект
    project.status_id = 0  # Возвращаем в статус "активный"
    project.position_index = max_position + 1  # Ставим в конец списка
    project.updated_date = datetime.now(timezone.utc)

    result = await db.execute(select(Task).where(cast((Task.project_id == project_id), Boolean)))
    # Нет необходимости проверять на удалённые задачи т.к. в удалённом проекте все задачи удалены
    tasks = result.scalars().all()

    task_counter = 0
    task_ids = []
    for task in tasks:
        # Устанавливаем базовый статус
        task.status_id = 0  # Временный статус "активный"
        task.position_index = task_counter
        task.updated_date = datetime.now(timezone.utc)

        # Если есть actual_completion_date - задача завершена
        if task.actual_completion_date:
            task.status_id = 1

        task_counter += 1
        task_ids.append(task.task_id)

    await db.commit()

    # проверяем просроченность у задач
    await check_overdue_tasks(current_user.user_id, task_ids, db)


    if project.actual_completion_date: # если есть дата завершения
        project.status_id = 1  # Проект завершен

    # Проверяем просроченность проекта (автоматически обновит статус на 2 если просрочено)
    new_project = await check_overdue_projects(current_user.user_id, [project_id], db)

    return new_project[0]

@router.post('/recover_task', response_model=TaskResponse)
async def recover_task(
        task_id: int = Query(..., description="ID задачи"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(cast(
        (Task.task_id == task_id) &
        (Task.user_id == current_user.user_id), Boolean
    )))

    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задача с ID {task_id} не найдена"
        )

    if task.status_id != 3:  # если не является удалённым
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Задача с ID {task_id} не является удалённой (текущий статус {task.status_id})"
        )

    # Находим максимальный position_index среди активных проектов пользователя
    max_pos_result = await db.execute(
        select(func.max(Task.position_index)).where(cast(
            (Task.user_id == current_user.user_id) &
            (Task.status_id != 3), Boolean  # Только не удалённые проекты
        ))
    )
    max_position = max_pos_result.scalar_one_or_none() or 0

    task.position_index = max_position + 1

    if task.actual_completion_date: # если есть дата завершения
        task.status_id = 1  # статус "завершённый"
    else:
        task.status_id = 0

    new_task = await check_overdue_tasks(current_user.user_id, [task_id], db) # проверка на просроченность

    task.updated_date = datetime.now(timezone.utc)
    await db.commit()

    return new_task[0]