import uuid
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.repositories import (
    LayerRepository,
    McaProjectRepository,
    TaskRepository,
    ResultRepository,
    ProjectCriterionRepository
)
from src.io.minio_raster_reader import MinIORasterReader
from src.io.minio_raster_writer import MinIORasterWriter
from src.io.postgis_vector_reader import PostGISVectorReader
from src.application.mca_orchestrator import McaOrchestrator

logger = logging.getLogger(__name__)


def run_task_from_project(task_id: uuid.UUID, db_url: str, minio_settings: dict):
    engine = create_engine(db_url)
    session = Session(engine)

    try:
        layer_repo = LayerRepository(session)
        project_repo = McaProjectRepository(session)
        task_repo = TaskRepository(session)
        result_repo = ResultRepository(session)
        criterion_repo = ProjectCriterionRepository(session)

        raster_reader = MinIORasterReader(
            minio_settings["endpoint"],
            minio_settings["access_key"],
            minio_settings["secret_key"],
            minio_settings["bucket"],
            minio_settings["secure"]
        )
        raster_writer = MinIORasterWriter(
            minio_settings["endpoint"],
            minio_settings["access_key"],
            minio_settings["secret_key"],
            minio_settings["bucket"],
            minio_settings["secure"]
        )
        vector_reader = PostGISVectorReader(db_url)

        orchestrator = McaOrchestrator(
            session=session,
            layer_repo=layer_repo,
            project_repo=project_repo,
            task_repo=task_repo,
            result_repo=result_repo,
            criterion_repo=criterion_repo,
            raster_reader=raster_reader,
            vector_reader=vector_reader,
            raster_writer=raster_writer
        )

        task_repo.update_status(task_id, "PROCESSING")
        orchestrator.run_from_project(task_id)

    except Exception as e:
        logger.exception(f"Task {task_id} failed")
        task_repo.update_status(task_id, "FAILED", error_message=str(e))
    finally:
        session.close()