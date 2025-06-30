from .run import app
from .dependencies import get_current_user


from .routers import get_router, post_router  # экспорт роутеров
from .data_base import Base, get_db  # если нужно экспортировать модели

__all__ = ['get_router', 'post_router', 'Base', 'get_db']  # явное указание экспортируемых объектов