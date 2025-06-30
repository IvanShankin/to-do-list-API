import datetime

import pytest
from httpx import AsyncClient, ASGITransport

from pyasn1.type.univ import Boolean
from sqlalchemy import select, update, cast, Boolean
from app.models.models import User, Project, Task
from app.run import app

class TestPostGeneral:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'user_data, status_code',
        [
            ({"login": "test", "password": "test_password", "email": "test_email@example.com"}, 200),
            ({"login": "another_login", "password": "strong_password", "email": "test_e3"}, 422)
        ]
    )
    async def test_create_user(self, user_data, status_code, db_session):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.post("/new_user", json=user_data)
            assert response.status_code == status_code

            if status_code == 200:
                result_db = await db_session.execute(
                    select(User).where(cast(User.login == user_data['login'], Boolean)))
                data = response.json()
                db_user = result_db.scalar_one_or_none()

                if status_code == 200:  # если статус 200, то будет добавлен в БД
                    assert isinstance(data["user_id"], int)  # Проверка типа
                    assert db_user.login == user_data['login']
                    assert db_user.email == user_data['email']
                    assert isinstance(data["created_date"], str)  # Проверка типа
                    assert isinstance(data["last_login"], str)  # Проверка типа
                else:  # в БД ничего не должно добавиться
                    assert not db_user

    # создание пользователей с идентичными данными
    @pytest.mark.asyncio
    async def test_create_user_identical(self):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response_first = await ac.post("/new_user",
                                           json={"login": "test", "password": "test_password",
                                                 "email": "test_email@example.com"})
            assert response_first.status_code == 200

            # попытка создать с логином который уже имеется
            response_second = await ac.post("/new_user",
                                            json={"login": "test", "password": "test_password",
                                                  "email": "another_email@example.com"})
            assert response_second.status_code == 400

            # попытка создать с почтой которая уже имеется
            response_third = await ac.post("/new_user",
                                           json={"login": "another_test", "password": "test_password",
                                                 "email": "test_email@example.com"})
            assert response_third.status_code == 400

    @pytest.mark.asyncio
    async def test_token(self, create_user):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.post("/token",
                                     data={
                                         "username": create_user['user_name'],
                                         "password": create_user['password']
                                     },
                                     headers={"Content-Type": "application/x-www-form-urlencoded"}
                                     )
            assert response.status_code == 200
            data = response.json()
            assert data['access_token']

    @pytest.mark.asyncio
    async def test_refresh_token(self, create_user):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.post("/refresh_token", json={"refresh_token": create_user['access_token']})
            assert response.status_code == 200
            data = response.json()
            assert data['access_token']


class TestPostProject:
    @pytest.mark.asyncio
    async def test_create_project(self, create_user, db_session):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.post("/create_project",
                                     json={"title": 'test_title',
                                           'description': 'test_description',
                                           "desired_completion_date": "2025-06-26T19:00:30.164Z"},
                                     headers={"Authorization": f"Bearer {create_user['access_token']}","Content-Type": "application/json"})
            assert response.status_code == 200
            data = response.json()

            query = await db_session.execute(select(Project).where(cast(Project.project_id == data['project_id'], Boolean)))
            result_db = query.scalar_one_or_none()

            assert result_db
            assert result_db.title == 'test_title'
            assert result_db.description == 'test_description'
            assert result_db.desired_completion_date == datetime.datetime.fromisoformat(
                "2025-06-26T19:00:30.164").replace(tzinfo=datetime.timezone.utc)



    @pytest.mark.asyncio
    async def test_update_project(self, db_session, create_project):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.post("/update_project",
                                     json={"project_id": create_project['project_id'],
                                           'position_index': 0,
                                           'title': 'test_title',
                                           'description': 'test_description',
                                           'status_id': 2, # статус просрочен
                                           "desired_completion_date": "2030-05-25T19:00:30.164Z",
                                           "actual_completion_date": "2025-06-28T07:45:39.971Z"
                                           },
                                     headers = {"Authorization": f"Bearer {create_project['data_user']['access_token']}",
                                               "Content-Type": "application/json"}
                                     )
            assert response.status_code == 200
            data = response.json()

            query = await db_session.execute(select(Project).where(cast(Project.project_id == create_project['project_id'], Boolean)))
            result_db = query.scalar_one_or_none()
            await db_session.refresh(result_db)

            assert result_db
            assert result_db.position_index == 0
            assert result_db.title == 'test_title'
            assert result_db.description == 'test_description'
            assert result_db.status_id == 1 # мы передали 2(просрочен), но тут должно быть 1(Завершено) т.к. передали дату завершения
            assert result_db.desired_completion_date == datetime.datetime.fromisoformat(
                "2030-05-25T19:00:30.164").replace(tzinfo=datetime.timezone.utc)
            assert result_db.actual_completion_date == datetime.datetime.fromisoformat(
                "2025-06-28T07:45:39.971").replace(tzinfo=datetime.timezone.utc)
            assert isinstance(data["updated_date"], str)  # Проверка типа



    @pytest.mark.asyncio
    @pytest.mark.parametrize('complete_remove',[True,False])
    async def test_delete_project(self,complete_remove, db_session, create_project):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.post("/delete_project",
                                     params={"project_id": create_project['project_id'], "complete_remove": complete_remove},
                                     headers={"Authorization": f"Bearer {create_project['data_user']['access_token']}"}
                                     )
            assert response.status_code == 200

            query = await db_session.execute(select(Project).where(cast(Project.project_id == create_project['project_id'], Boolean)))
            result_db = query.scalar_one_or_none()

            if complete_remove: # если стоит флаг полного удаления (должно удалиться с БД)
                assert not result_db
            else:
                await db_session.refresh(result_db)
                assert result_db
                assert result_db.status_id == 3 # статус удалён

    @pytest.mark.asyncio
    async def test_recover_project(self, db_session, create_project):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            await db_session.execute(update(Project).where(cast(
                (Project.project_id == create_project['project_id']), Boolean)
                ).values(status_id=3, position_index=-1)  # статус = удалённый
                                    )  # помечаем в БД, что проект удален
            await db_session.commit()

            response = await ac.post("/recover_project",
                                     params={"project_id": create_project['project_id']},
                                     headers={"Authorization": f"Bearer {create_project['data_user']['access_token']}"}
                                     )
            assert response.status_code == 200

            query = await db_session.execute(select(Project).where(cast(Project.project_id == create_project['project_id'], Boolean)))
            result_db = query.scalar_one_or_none()

            assert result_db
            assert result_db.status_id != 3 # не равен "удалён"



class TestPostTask:
    @pytest.mark.asyncio
    async def test_create_task(self, db_session, create_project):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.post("/create_task",
                                     json={"project_id": create_project['project_id'],
                                           'title': 'test',
                                           'description': 'test',
                                           'priority': 0,
                                           "desired_completion_date": "2025-06-26T19:00:30.164Z"},
                                     headers={"Authorization": f"Bearer {create_project['data_user']['access_token']}",
                                              "Content-Type": "application/json"})
            assert response.status_code == 200
            data = response.json()

            query = await db_session.execute(select(Task).where(cast(Task.task_id == data['task_id'], Boolean)))
            result_db = query.scalar_one_or_none()

            assert result_db
            assert result_db.project_id == result_db.project_id
            assert result_db.title == 'test'
            assert result_db.description == 'test'
            assert result_db.priority == 0
            assert result_db.desired_completion_date == datetime.datetime.fromisoformat(
                "2025-06-26T19:00:30.164").replace(tzinfo=datetime.timezone.utc)

    @pytest.mark.asyncio
    async def test_update_task(self, db_session, create_task):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.post("/update_task",
                                     json={"task_id": create_task['task_id'],
                                           "status_id": 2,
                                           "position_index": 0,
                                           "priority": 2,
                                           "title": "test_title",
                                           "description": "test_description",
                                           "desired_completion_date": "2030-05-25T19:00:30.164Z",
                                           "actual_completion_date": "2025-06-28T07:45:39.971Z"
                                           },
                                     headers={"Authorization": f"Bearer {create_task['data_user']['access_token']}",
                                              "Content-Type": "application/json"}
                                     )
            assert response.status_code == 200
            data = response.json()

            query = await db_session.execute(select(Task).where(cast(Task.task_id == create_task['task_id'], Boolean)))
            result_db = query.scalar_one_or_none()
            await db_session.refresh(result_db)

            assert result_db
            assert result_db.status_id == 1  # мы передали 2(просрочен), но тут должно быть 1(Завершено) т.к. передали дату завершения
            assert result_db.position_index == 0
            assert result_db.priority == 2
            assert result_db.title == 'test_title'
            assert result_db.description == 'test_description'
            assert result_db.desired_completion_date == datetime.datetime.fromisoformat(
                "2030-05-25T19:00:30.164").replace(tzinfo=datetime.timezone.utc)
            assert result_db.actual_completion_date == datetime.datetime.fromisoformat(
                "2025-06-28T07:45:39.971").replace(tzinfo=datetime.timezone.utc)
            assert isinstance(data["updated_date"], str)  # Проверка типа

    @pytest.mark.asyncio
    @pytest.mark.parametrize('complete_remove', [True, False])
    async def test_delete_task(self, complete_remove, db_session, create_task):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.post("/delete_task",
                                     params={"task_id": create_task['task_id'],
                                             "complete_remove": complete_remove},
                                     headers={"Authorization": f"Bearer {create_task['data_user']['access_token']}"}
                                     )
            assert response.status_code == 200

            query = await db_session.execute(
                select(Task).where(cast(Task.project_id == create_task['project_id'], Boolean)))
            result_db = query.scalar_one_or_none()

            if complete_remove:  # если стоит флаг полного удаления (должно удалиться с БД)
                assert not result_db
            else:
                await db_session.refresh(result_db)
                assert result_db
                assert result_db.status_id == 3  # статус удалён

    @pytest.mark.asyncio
    async def test_recover_task(self, db_session, create_task):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            await db_session.execute(update(Task).where(cast(
                (Task.task_id == create_task['task_id']), Boolean)
            ).values(status_id=3, position_index=-1)  # статус = удалённый
                                     )  # помечаем в БД, что проект удален
            await db_session.commit()

            response = await ac.post("/recover_task",
                                     params={"task_id": create_task['task_id']},
                                     headers={"Authorization": f"Bearer {create_task['data_user']['access_token']}"}
                                     )
            assert response.status_code == 200

            query = await db_session.execute(
                select(Task).where(cast(Task.task_id == create_task['task_id'], Boolean)))
            result_db = query.scalar_one_or_none()

            assert result_db
            assert result_db.status_id != 3  # не равен "удалён"