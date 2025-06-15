from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    login: str
    password: str
    email: EmailStr

class TokenData(BaseModel):
    username: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ProjectCreate(BaseModel):
    title: str = Field(..., max_length=100) # "..." - это значит что поле обязательное
    description: Optional[str] = Field(None, max_length=500)
    desired_completion_date: Optional[datetime] = None

class UpdateProject(BaseModel):
    project_id: int
    position_index: Optional[int] = Field(None, ge=0)
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status_id: Optional[int] = Field(None, ge=0, le=2) # нет status_id = 3 т.к. для удаления используется отдельный эндопойнт
    desired_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

class TaskCreate(BaseModel):
    project_id: int
    title: str = Field(..., max_length=200)
    description: Optional[str] = Field(..., max_length=1000)
    priority: Optional[int] = Field(default=0, ge=0, le=2) # от 0 до 2 (чем выше приоритет тем важнее задача)
    desired_completion_date: Optional[datetime] = None

class UpdateTask(BaseModel):
    task_id: int
    status_id: Optional[int] = Field(None, ge=0, le=2) # нет status_id = 3 т.к. для удаления используется отдельный эндопойнт
    position_index: Optional[int] = Field(None, ge=0)
    priority: Optional[int] = Field(None, ge=0, le=2)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    desired_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None

