# To-Do List API

FastAPI приложение для управления проектами и задачами с аутентификацией пользователей.

## Особенности

- Асинхронное взаимодействие с базой данных (PostgreSQL)
- JWT аутентификация
- Управление проектами и задачами
- Система статусов (в работе, завершено, просрочено, удалено)
- Приоритеты задач
- Архивирование вместо полного удаления
- Автоматическая проверка просроченных задач/проектов

## Установка

1. Клонируйте репозиторий:
   ```bash
   git clone <ваш-репозиторий>
   cd <папка-проекта>
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
   Или установите вручную:
   ```bash
   pip install fastapi uvicorn asyncpg python-jose[cryptography] passlib bcrypt python-dotenv
   ```

3. Создайте файл `.env` в корне проекта:
   ```
   SECRET_KEY=ваш_секретный_ключ
   ```

4. Настройте подключение к БД в `app/config.py`

## Запуск

```bash
uvicorn app.run:app --reload
```

Приложение будет доступно по адресу: `http://localhost:8000`

## API Документация

После запуска доступны:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Структура проекта

```
app/
├── data_base/        # Настройки базы данных
├── models/           # Модели SQLAlchemy
├── routers/          # Роутеры API
├── schemas/          # Pydantic схемы
├── config.py         # Конфигурация приложения
├── dependencies.py   # Зависимости и утилиты
└── run.py            # Точка входа
```

## Модели данных

### Статусы
- `0` - В работе (in_progress)
- `1` - Завершено (completed)
- `2` - Просрочено (overdue)
- `3` - Удалено (deleted)

### Приоритеты задач
- `0` - Низкий
- `1` - Средний
- `2` - Высокий

## Основные эндпоинты

### Аутентификация
- `POST /token` - Получение JWT токена
- `POST /refresh_token` - Обновление токена
- `POST /new_user/user` - Регистрация нового пользователя

### Проекты
- `POST /create_project` - Создать проект
- `GET /get_project` - Получить проект(ы)
- `POST /update_project` - Обновить проект
- `POST /delete_project` - Удалить/архивировать проект
- `POST /recover_project` - Восстановить из архива

### Задачи
- `POST /create_tasks` - Создать задачу
- `GET /get_task` - Получить задачу(и)
- `POST /update_task` - Обновить задачу
- `POST /delete_task` - Удалить/архивировать задачу
- `POST /recover_task` - Восстановить из архива

## Примеры запросов

Создание пользователя:
```
POST /new_user/user
{
  "login": "user123",
  "password": "securepassword",
  "email": "user@example.com"
}
```

Создание проекта:
```
POST /create_project
{
  "title": "Мой проект",
  "description": "Описание проекта",
  "desired_completion_date": "2023-12-31T00:00:00Z"
}
```

## Особенности

- Все даты и время хранятся и возвращаются в формате **UTC**
- Автоматическая конвертация входящих дат в UTC
- Просроченные задачи определяются относительно текущего времени UTC

## Технологии

- Python 3.9+
- FastAPI
- SQLAlchemy (асинхронный режим)
- PostgreSQL
- JWT для аутентификации
- Pydantic для валидации данных