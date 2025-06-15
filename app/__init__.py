from .run import app
from .dependencies import get_db, get_current_user


from .routers import get_router, post_router  # экспорт роутеров
from .data_base import Base  # если нужно экспортировать модели

__all__ = ['get_router', 'post_router', 'Base']  # явное указание экспортируемых объектов