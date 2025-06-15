import uvicorn
from fastapi import FastAPI
from app.routers import get_router, post_router

app = FastAPI()

app.include_router(get_router)
app.include_router(post_router)

if __name__ == "__main__":
    uvicorn.run(
        "run:app",  # файл для запуска сервера
        host="0.0.0.0",
        port=8000,
        reload=True
    )