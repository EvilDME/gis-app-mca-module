import os
import time
import logging
from sqlalchemy import create_engine, text

from src.io.minio_raster_reader import MinIORasterReader
from src.io.minio_raster_writer import MinIORasterWriter
from src.io.local_vector_reader import LocalVectorReader
from src.application.mca_orchestrator import McaOrchestrator
from src.db.models import Base
from src.utils.vector_loader import init_vector_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_db(db_url: str, max_retries: int = 30, retry_interval: int = 2):
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
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()
    Base.metadata.create_all(engine)
    logger.info("ORM tables initialized.")


def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not set")

    # MinIO параметры
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket = os.getenv("MINIO_BUCKET", "rasters")
    minio_secure = os.getenv("MINIO_SECURE", "False").lower() == "true"

    engine = wait_for_db(db_url)
    init_db(engine)
    init_vector_data(engine, data_dir="/app/data/vector", schema="vector_data")

    # Создаём MinIO ридеры и врайтеры
    raster_reader = MinIORasterReader(minio_endpoint, minio_access, minio_secret, minio_bucket, minio_secure)
    raster_writer = MinIORasterWriter(minio_endpoint, minio_access, minio_secret, minio_bucket, minio_secure)
    vector_reader = LocalVectorReader()  # векторы пока из файлов, можно позже заменить на PostGIS

    app = McaOrchestrator(raster_reader, vector_reader, raster_writer)
    app.run_project("data/projects/suitability_project.json")

if __name__ == "__main__":
    main()