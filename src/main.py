# src/main_json.py
import os
import logging
from dotenv import load_dotenv
from src.io.minio_raster_reader import MinIORasterReader
from src.io.minio_raster_writer import MinIORasterWriter
from src.io.postgis_vector_reader import PostGISVectorReader
from src.application.mca_orchestrator import McaOrchestrator

load_dotenv()
logging.basicConfig(level=logging.INFO)

def main():
    db_url = os.getenv("DATABASE_URL")
    minio_endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    minio_access = os.getenv("MINIO_ROOT_USER", "minioadmin")
    minio_secret = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
    minio_bucket = os.getenv("MINIO_BUCKET", "rasters")
    minio_secure = False

    raster_reader = MinIORasterReader(minio_endpoint, minio_access, minio_secret, minio_bucket, minio_secure)
    raster_writer = MinIORasterWriter(minio_endpoint, minio_access, minio_secret, minio_bucket, minio_secure)
    vector_reader = PostGISVectorReader(db_url)

    orchestrator = McaOrchestrator(raster_reader, vector_reader, raster_writer)
    orchestrator.run_project("data/projects/suitability_minio_postgis.json")

if __name__ == "__main__":
    main()