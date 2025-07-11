import uvicorn
import asyncio
from fastapi import FastAPI
from routers import get_router, post_router
from app.data_base.data_base import create_database

app = FastAPI()

app.include_router(get_router)
app.include_router(post_router)

if __name__ == "__main__":
    asyncio.run(create_database())
    uvicorn.run(
        "run:app",  # файл для запуска сервера
        host="0.0.0.0",
        port=8000,
        reload=True
    )