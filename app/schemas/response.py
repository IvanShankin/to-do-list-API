from pydantic import BaseModel, Field
from datetime import datetime
from typing import Annotated, Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    user_id: int
    login: str
    email: str
    created_date: datetime
    last_login: datetime

class Status(BaseModel):
    status_id: int
    name: str

class TaskResponse(BaseModel):
    task_id: int
    user_id: int
    status: Status
    project_id: int
    position_index: int
    priority: int
    title: str
    description: str
    created_date: Annotated[datetime, Field(..., title="Дата создания")]
    desired_completion_date: Optional[Annotated[datetime, Field(..., title="Дата желаемого завершения")]] = None
    actual_completion_date: Optional[Annotated[datetime, Field(..., title="Дата фактического завершения")]] = None
    updated_date: Annotated[datetime, Field(..., title="Дата обновления")]

class ProjectResponse(BaseModel):
    project_id: int
    user_id: int
    position_index: int
    title: str
    description: str
    status: Status
    created_date: Annotated[datetime, Field(..., title="Дата создания")]
    desired_completion_date: Optional[Annotated[datetime, Field(..., title="Дата желаемого завершения")]] = None
    actual_completion_date: Optional[Annotated[datetime, Field(..., title="Дата фактического завершения")]] = None
    updated_date: Annotated[datetime, Field(..., title="Дата обновления")]

class DeleteProjectResponse(BaseModel):
    message: str
    project_id: int
    deleted_at: datetime
    affected_tasks_count: Annotated[int, Field(None, title="Количество удалённых задач")]

class DeleteTaskResponse(BaseModel):
    message: str
    task_id: int
    project_id: int
    deleted_at: datetime
    affected_tasks_count: int





