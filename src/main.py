# src/main.py
import os
import sys
import time
import uuid
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Импорт собственных модулей
from src.db.models import Base
from src.db.repositories import (
    LayerRepository, McaProjectRepository,
    TaskRepository, ResultRepository
)
from src.io.minio_raster_reader import MinIORasterReader
from src.io.minio_raster_writer import MinIORasterWriter
from src.io.postgis_vector_reader import PostGISVectorReader
from src.application.mca_orchestrator import McaOrchestrator
from src.utils.vector_loader import init_vector_data

# Загружаем переменные окружения из .env (если файл существует)
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_db(db_url: str, max_retries: int = 30, retry_interval: int = 2):
    """Ожидание готовности PostgreSQL."""
    engine = create_engine(db_url)
    for i in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database is ready.")
            return engine
        except OperationalError as e:
            logger.warning(f"Database not ready yet (attempt {i+1}/{max_retries}): {e}")
            time.sleep(retry_interval)
    raise RuntimeError("Could not connect to database after multiple retries.")


def init_db(engine):
    """Активация PostGIS и создание отсутствующих таблиц ORM."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    Base.metadata.create_all(engine)
    logger.info("ORM tables initialized.")


def main():
    # --- Чтение переменных окружения ---
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")

    minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access_key = os.getenv("MINIO_ROOT_USER", "minioadmin")      # ← изменено
    minio_secret_key = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")  # ← изменено
    minio_bucket = os.getenv("MINIO_BUCKET", "rasters")
    minio_secure = os.getenv("MINIO_SECURE", "False").lower() == "true"

    # Проверка обязательных переменных MinIO
    if not minio_access_key or not minio_secret_key:
        raise ValueError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be set")

    # ID проекта из аргумента командной строки или переменной окружения
    project_id_str = None
    if len(sys.argv) > 1:
        project_id_str = sys.argv[1]
    else:
        project_id_str = os.getenv("PROJECT_ID")
    if not project_id_str:
        raise ValueError("Project ID must be provided as argument or via PROJECT_ID env variable")
    try:
        project_id = uuid.UUID(project_id_str)
    except ValueError:
        raise ValueError(f"Invalid project ID: {project_id_str}")

    # --- Инициализация БД ---
    engine = wait_for_db(db_url)
    init_db(engine)

    # Загрузка векторных данных из шейпфайлов (если ещё не загружены)
    init_vector_data(engine, data_dir="/app/data/vector", schema="vector_data")

    # Создание сессии и репозиториев
    session = Session(engine)
    layer_repo = LayerRepository(session)
    project_repo = McaProjectRepository(session)
    task_repo = TaskRepository(session)
    result_repo = ResultRepository(session)

    # Создание ридеров и врайтеров
    raster_reader = MinIORasterReader(
        endpoint=minio_endpoint,
        access_key=minio_access_key,
        secret_key=minio_secret_key,
        bucket=minio_bucket,
        secure=minio_secure
    )
    raster_writer = MinIORasterWriter(
        endpoint=minio_endpoint,
        access_key=minio_access_key,
        secret_key=minio_secret_key,
        bucket=minio_bucket,
        secure=minio_secure
    )
    vector_reader = PostGISVectorReader(db_url)

    # Создание оркестратора
    orchestrator = McaOrchestrator(
        session=session,
        layer_repo=layer_repo,
        project_repo=project_repo,
        task_repo=task_repo,
        result_repo=result_repo,
        raster_reader=raster_reader,
        vector_reader=vector_reader,
        raster_writer=raster_writer
    )

    # Запуск анализа
    logger.info(f"Starting MCA project {project_id}")
    orchestrator.run_project(project_id)


if __name__ == "__main__":
    main()