from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.data_base.base import Base

# этот файл описывает каждую таблицу в БД

class User(Base): # Создание таблицы
    __tablename__  = 'users' # имя таблицы
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    login= Column(String(100), unique=True, nullable=False)
    password= Column(String(255), nullable=False)
    email = Column(String(100), unique=True)
    created_date= Column(DateTime(timezone=True), nullable=False)
    last_login= Column(DateTime(timezone=True), nullable=False)

    # Связи
    projects = relationship("Project", back_populates="user")
    tasks = relationship("Task", back_populates="user")

class Status(Base):
    __tablename__ = 'statuses'  # имя таблицы
    status_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), unique=True, nullable=False)

    # Связь с задачами
    tasks = relationship("Task", back_populates="status")
    projects = relationship("Project", back_populates="status")

class Project(Base):
    __tablename__  = 'projects'
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    position_index = Column(Integer)
    title = Column(String(100), nullable=False)
    description = Column(String(500))
    status_id = Column(Integer, ForeignKey("statuses.status_id"), default=0)
    created_date = Column(DateTime(timezone=True), nullable=False)
    desired_completion_date = Column(DateTime(timezone=True))
    actual_completion_date = Column(DateTime(timezone=True))
    updated_date = Column(DateTime(timezone=True))

    # Связи
    user = relationship("User", back_populates="projects")
    status = relationship("Status", back_populates="projects")
    tasks = relationship("Task", back_populates="project")

class Task(Base):
    __tablename__  = 'tasks'
    task_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    status_id = Column(Integer, ForeignKey("statuses.status_id"), default=0)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    position_index = Column(Integer, nullable=False)
    priority = Column(Integer, default=0) # приоритет от 0 до 2 (низкий, средний, высокий)
    title = Column(String(200), nullable=False)
    description = Column(String(1000))
    created_date = Column(DateTime(timezone=True), nullable=False)
    desired_completion_date = Column(DateTime(timezone=True))
    actual_completion_date = Column(DateTime(timezone=True))
    updated_date = Column(DateTime(timezone=True))

    # Связи
    user = relationship("User", back_populates="tasks")
    status = relationship("Status", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")

