import os
from fastapi import FastAPI
from dotenv import load_dotenv

from src.api.routes import router

# Загружаем переменные окружения из .env (если есть)
load_dotenv()

app = FastAPI(
    title="MCA GIS Service API",
    description="Модуль анализа пригодности территории для экотуризма",
)

# Подключаем роутер с эндпоинтами
app.include_router(router)

@app.get("/health")
def health_check():
    """Проверка работоспособности сервиса."""
    return {"status": "ok", "service": "mca-gis"}

@app.get("/")
def root():
    return {"message": "MCA GIS Service is running. "}