import datetime
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient, ASGITransport

from app.run import app


def compare_dates(api_date_str, expected_dt):
    """Вернёт False если даты не совпадают"""
    # Преобразуем строку из API в datetime объект
    api_dt = datetime.fromisoformat(api_date_str.replace('Z', '+00:00'))
    # Сравниваем с допуском 1 секунда
    return abs(api_dt - expected_dt) < timedelta(seconds=1)

class TestGetRequest:
    @pytest.mark.asyncio
    async def test_get_me(self, db_session, create_user):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.get("/user_me/",headers={"Authorization": f"Bearer {create_user['access_token']}"})
            assert response.status_code == 200
            data = response.json()

            assert data['user_id'] == create_user['user_id']
            assert data['login'] == create_user['user_name']
            assert data['email'] == create_user['email']

    @pytest.mark.asyncio
    async def test_get_projects(self, db_session, create_project):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            response = await ac.get("/get_projects/",
                                    params={'project_id': create_project['project_id']},
                                    headers={"Authorization": f"Bearer {create_project['data_user']['access_token']}"}
                                    )
            assert response.status_code == 200
            data = response.json()


            assert data[0]['user_id'] == create_project['data_user']['user_id']
            assert data[0]['project_id'] == create_project['project_id']
            assert data[0]['title'] == create_project['title']
            assert data[0]['description'] == create_project['description']
            assert data[0]['status']['status_id'] == 0
            assert data[0]['status']['name'] == 'in_progress'
            assert compare_dates(data[0]['created_date'], create_project['created_date'])
            assert compare_dates(data[0]['desired_completion_date'], create_project['desired_completion_date'])
            assert not data[0]['actual_completion_date']
            assert compare_dates(data[0]['updated_date'], create_project['created_date'])


    @pytest.mark.asyncio
    async def test_get_tasks(self, db_session, create_task):
        async with AsyncClient(
                transport=ASGITransport(app),
                base_url="http://test",
        ) as ac:
            # посылаем только id проекта
            response = await ac.get("/get_tasks/",
                                    params={'project_id': create_task['project_id']},
                                    headers={"Authorization": f"Bearer {create_task['data_user']['access_token']}"}
                                    )
            assert response.status_code == 200
            data = response.json()

            assert data
            assert data[0]['user_id'] == create_task['data_user']['user_id']
            assert data[0]['project_id'] == create_task['project_id']
            assert data[0]['status']['status_id'] == 0
            assert data[0]['status']['name'] == 'in_progress'
            assert data[0]['project_id'] == create_task['project_id']
            assert data[0]['position_index'] == create_task['position_index']
            assert data[0]['priority'] == create_task['priority']
            assert data[0]['title'] == create_task['title']
            assert data[0]['description'] == create_task['description']
            assert compare_dates(data[0]['created_date'], create_task['created_date'])
            assert compare_dates(data[0]['desired_completion_date'], create_task['desired_completion_date'])
            assert not data[0]['actual_completion_date']
            assert compare_dates(data[0]['updated_date'], create_task['created_date'])

            # посылаем только id задачи
            response = await ac.get("/get_tasks/",
                                    params={'task_id': create_task['task_id']},
                                    headers={"Authorization": f"Bearer {create_task['data_user']['access_token']}"}
                                    )
            assert response.status_code == 200
            data_second = response.json()

            assert data_second
            assert data_second[0]['user_id'] == create_task['data_user']['user_id']
            assert data_second[0]['project_id'] == create_task['project_id']
            assert data_second[0]['status']['status_id'] == 0
            assert data_second[0]['status']['name'] == 'in_progress'
            assert data_second[0]['project_id'] == create_task['project_id']
            assert data_second[0]['position_index'] == create_task['position_index']
            assert data_second[0]['priority'] == create_task['priority']
            assert data_second[0]['title'] == create_task['title']
            assert data_second[0]['description'] == create_task['description']
            assert compare_dates(data_second[0]['created_date'], create_task['created_date'])
            assert compare_dates(data_second[0]['desired_completion_date'], create_task['desired_completion_date'])
            assert not data_second[0]['actual_completion_date']
            assert compare_dates(data_second[0]['updated_date'], create_task['created_date'])
