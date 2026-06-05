import os
from functools import lru_cache
from fastapi import Depends, HTTPException, Header
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import jwt

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
from src.services.layer_selector import LayerSelector


@lru_cache()
def get_settings():
    return {
        "db_url": os.getenv("DATABASE_URL"),
        "minio_endpoint": os.getenv("MINIO_ENDPOINT", "minio:9000"),
        "minio_access_key": os.getenv("MINIO_ROOT_USER", "minioadmin"),
        "minio_secret_key": os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
        "minio_bucket": os.getenv("MINIO_BUCKET", "rasters"),
        "minio_secure": os.getenv("MINIO_SECURE", "False").lower() == "true",
        "jwt_secret": os.getenv("JWT_SECRET"),
        "minio_public_host": os.getenv("MINIO_PUBLIC_HOST", "localhost"),
    }


def get_db_session():
    settings = get_settings()
    engine = create_engine(settings["db_url"])
    with Session(engine) as session:
        yield session


def get_layer_repo(session: Session = Depends(get_db_session)):
    return LayerRepository(session)


def get_project_repo(session: Session = Depends(get_db_session)):
    return McaProjectRepository(session)


def get_task_repo(session: Session = Depends(get_db_session)):
    return TaskRepository(session)


def get_result_repo(session: Session = Depends(get_db_session)):
    return ResultRepository(session)


def get_criterion_repo(session: Session = Depends(get_db_session)):
    return ProjectCriterionRepository(session)


def get_raster_reader():
    settings = get_settings()
    return MinIORasterReader(
        settings["minio_endpoint"],
        settings["minio_access_key"],
        settings["minio_secret_key"],
        settings["minio_bucket"],
        settings["minio_secure"]
    )


def get_raster_writer():
    settings = get_settings()
    return MinIORasterWriter(
        settings["minio_endpoint"],
        settings["minio_access_key"],
        settings["minio_secret_key"],
        settings["minio_bucket"],
        settings["minio_secure"]
    )


def get_vector_reader():
    settings = get_settings()
    return PostGISVectorReader(settings["db_url"])


def get_layer_selector(session: Session = Depends(get_db_session)):
    return LayerSelector(session)


def get_orchestrator(
    session: Session = Depends(get_db_session),
    layer_repo=Depends(get_layer_repo),
    project_repo=Depends(get_project_repo),
    task_repo=Depends(get_task_repo),
    result_repo=Depends(get_result_repo),
    criterion_repo=Depends(get_criterion_repo),
    raster_reader=Depends(get_raster_reader),
    raster_writer=Depends(get_raster_writer),
    vector_reader=Depends(get_vector_reader)
):
    from src.application.mca_orchestrator import McaOrchestrator
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
    return orchestrator


# ------------- JWT аутентификация -------------
def get_current_user(authorization: str = Header(...)):
    """
    Извлекает и верифицирует JWT токен из заголовка Authorization.
    Возвращает словарь с user_id и username.
    """
    
    settings = get_settings()
    secret = settings.get("jwt_secret")
    if not secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET not configured")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]

    print("Received token:", token[:50] if token else "None")
    
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        user_id = payload.get("id") or payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"user_id": str(user_id), "username": payload.get("username")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")