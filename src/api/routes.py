import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from shapely.geometry import shape as shapely_shape
from geoalchemy2.shape import from_shape

from src.api import schemas
from src.api.dependencies import (
    get_db_session,
    get_project_repo,
    get_task_repo,
    get_result_repo,
    get_criterion_repo,
    get_settings,
    get_current_user,
)
from src.services.task_worker import run_task_from_project

router = APIRouter()

# --------------------- ПРОЕКТЫ ---------------------

@router.post("/projects", response_model=schemas.ProjectResponse)
def create_project(
    data: schemas.ProjectCreateRequest,
    user = Depends(get_current_user),
    project_repo = Depends(get_project_repo)
):
    user_id = user["user_id"]
    shapely_poly = shapely_shape(data.study_area)
    study_area_wkb = from_shape(shapely_poly, srid=4326)
    project = project_repo.create(
        user_id=user_id,
        name=data.name,
        aggregation_method=data.aggregation_method,
        study_area=study_area_wkb
    )
    return schemas.ProjectResponse(
        id=project.id,
        name=project.name,
        user_id=project.user_id,
        aggregation_method=project.aggregation_method,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@router.post("/projects/with-criteria", response_model=schemas.ProjectWithCriteriaResponse)
def create_project_with_criteria(
    data: schemas.ProjectWithCriteriaCreateRequest,
    user = Depends(get_current_user),
    project_repo = Depends(get_project_repo),
    criterion_repo = Depends(get_criterion_repo)
):
    user_id = user["user_id"]
    shapely_poly = shapely_shape(data.study_area)
    study_area_wkb = from_shape(shapely_poly, srid=4326)

    project = project_repo.create(
        user_id=user_id,
        name=data.name,
        aggregation_method=data.aggregation_method,
        study_area=study_area_wkb
    )

    created_criteria = []
    for crit_data in data.criteria:
        criterion = criterion_repo.create(
            project_id=project.id,
            weight=crit_data.weight,
            analysis_type=crit_data.analysis_type,
            data_type=crit_data.data_type,
            logic_params=crit_data.logic_params
        )
        created_criteria.append(schemas.CriterionResponse(
            id=criterion.id,
            project_id=criterion.project_id,
            analysis_type=criterion.analysis_type,
            data_type=criterion.data_type,
            weight=criterion.weight,
            logic_params=criterion.logic_params,
            created_at=criterion.created_at
        ))

    return schemas.ProjectWithCriteriaResponse(
        id=project.id,
        name=project.name,
        user_id=project.user_id,
        aggregation_method=project.aggregation_method,
        created_at=project.created_at,
        updated_at=project.updated_at,
        criteria=created_criteria
    )

@router.get("/projects", response_model=List[schemas.ProjectResponse])
def list_projects(
    user = Depends(get_current_user),
    project_repo = Depends(get_project_repo)
):
    projects = project_repo.get_by_user(user["user_id"])
    return [
        schemas.ProjectResponse(
            id=p.id,
            name=p.name,
            user_id=p.user_id,
            aggregation_method=p.aggregation_method,
            created_at=p.created_at,
            updated_at=p.updated_at
        ) for p in projects
    ]

@router.get("/projects/{project_id}", response_model=schemas.ProjectWithCriteriaResponse)
def get_project(
    project_id: uuid.UUID,
    include_criteria: bool = True,
    user = Depends(get_current_user),
    project_repo = Depends(get_project_repo),
    criterion_repo = Depends(get_criterion_repo)
):
    project = project_repo.get_by_id(project_id, load_criteria=include_criteria)
    if not project or project.user_id != user["user_id"]:
        raise HTTPException(404, "Project not found")

    criteria = []
    if include_criteria:
        if hasattr(project, 'criteria') and project.criteria is not None:
            criteria_list = project.criteria
        else:
            criteria_list = criterion_repo.get_by_project(project_id)
        criteria = [
            schemas.CriterionResponse(
                id=c.id,
                project_id=c.project_id,
                analysis_type=c.analysis_type,
                data_type=c.data_type,
                weight=c.weight,
                logic_params=c.logic_params,
                created_at=c.created_at
            ) for c in criteria_list
        ]

    return schemas.ProjectWithCriteriaResponse(
        id=project.id,
        name=project.name,
        user_id=project.user_id,
        aggregation_method=project.aggregation_method,
        created_at=project.created_at,
        updated_at=project.updated_at,
        criteria=criteria
    )

@router.put("/projects/{project_id}")
def update_project(
    project_id: uuid.UUID,
    update_data: schemas.ProjectUpdateRequest,
    user = Depends(get_current_user),
    project_repo = Depends(get_project_repo)
):
    project = project_repo.get_by_id(project_id, load_criteria=False)
    if not project or project.user_id != user["user_id"]:
        raise HTTPException(404, "Project not found")
    updates = {}
    if update_data.name is not None:
        updates["name"] = update_data.name
    if update_data.aggregation_method is not None:
        updates["aggregation_method"] = update_data.aggregation_method
    if update_data.study_area is not None:
        shapely_poly = shapely_shape(update_data.study_area)
        updates["study_area"] = from_shape(shapely_poly, srid=4326)
    if updates:
        project_repo.update(project_id, **updates)
    return {"status": "updated"}

@router.delete("/projects/{project_id}")
def delete_project(
    project_id: uuid.UUID,
    user = Depends(get_current_user),
    project_repo = Depends(get_project_repo)
):
    project = project_repo.get_by_id(project_id, load_criteria=False)
    if not project or project.user_id != user["user_id"]:
        raise HTTPException(404, "Project not found")
    project_repo.delete(project_id)
    return {"status": "deleted"}

# --------------------- КРИТЕРИИ ---------------------

@router.post("/projects/{project_id}/criteria", response_model=schemas.CriterionResponse)
def add_criterion(
    project_id: uuid.UUID,
    data: schemas.CriterionCreateRequest,
    user = Depends(get_current_user),
    project_repo = Depends(get_project_repo),
    criterion_repo = Depends(get_criterion_repo)
):
    project = project_repo.get_by_id(project_id, load_criteria=False)
    if not project or project.user_id != user["user_id"]:
        raise HTTPException(404, "Project not found")
    criterion = criterion_repo.create(
        project_id=project_id,
        weight=data.weight,
        analysis_type=data.analysis_type,
        data_type=data.data_type,
        logic_params=data.logic_params
    )
    return schemas.CriterionResponse(
        id=criterion.id,
        project_id=criterion.project_id,
        analysis_type=criterion.analysis_type,
        data_type=criterion.data_type,
        weight=criterion.weight,
        logic_params=criterion.logic_params,
        created_at=criterion.created_at
    )

@router.get("/projects/{project_id}/criteria", response_model=List[schemas.CriterionResponse])
def list_criteria(
    project_id: uuid.UUID,
    user = Depends(get_current_user),
    project_repo = Depends(get_project_repo),
    criterion_repo = Depends(get_criterion_repo)
):
    project = project_repo.get_by_id(project_id, load_criteria=False)
    if not project or project.user_id != user["user_id"]:
        raise HTTPException(404, "Project not found")
    criteria = criterion_repo.get_by_project(project_id)
    return [
        schemas.CriterionResponse(
            id=c.id,
            project_id=c.project_id,
            analysis_type=c.analysis_type,
            data_type=c.data_type,
            weight=c.weight,
            logic_params=c.logic_params,
            created_at=c.created_at
        ) for c in criteria
    ]

@router.put("/criteria/{criterion_id}")
def update_criterion(
    criterion_id: uuid.UUID,
    update_data: schemas.CriterionUpdateRequest,
    user = Depends(get_current_user),
    criterion_repo = Depends(get_criterion_repo),
    project_repo = Depends(get_project_repo)
):
    crit = criterion_repo.get_by_id(criterion_id)
    if not crit:
        raise HTTPException(404, "Criterion not found")
    project = project_repo.get_by_id(crit.project_id, load_criteria=False)
    if not project or project.user_id != user["user_id"]:
        raise HTTPException(403, "Access denied")
    updates = {}
    if update_data.weight is not None:
        updates["weight"] = update_data.weight
    if update_data.logic_params is not None:
        updates["logic_params"] = update_data.logic_params
    if updates:
        criterion_repo.update(criterion_id, **updates)
    return {"status": "updated"}

@router.delete("/criteria/{criterion_id}")
def delete_criterion(
    criterion_id: uuid.UUID,
    user = Depends(get_current_user),
    criterion_repo = Depends(get_criterion_repo),
    project_repo = Depends(get_project_repo)
):
    crit = criterion_repo.get_by_id(criterion_id)
    if not crit:
        raise HTTPException(404, "Criterion not found")
    project = project_repo.get_by_id(crit.project_id, load_criteria=False)
    if not project or project.user_id != user["user_id"]:
        raise HTTPException(403, "Access denied")
    criterion_repo.delete(criterion_id)
    return {"status": "deleted"}

# --------------------- ЗАПУСК ЗАДАЧ ---------------------

@router.post("/projects/{project_id}/run")
def run_project_analysis(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user = Depends(get_current_user),
    task_repo = Depends(get_task_repo),
    project_repo = Depends(get_project_repo),
    settings = Depends(get_settings)
):
    project = project_repo.get_by_id(project_id, load_criteria=True)
    if not project or project.user_id != user["user_id"]:
        raise HTTPException(404, "Project not found")
    task = task_repo.create(
        project_id=project.id,
        user_id=user["user_id"],
        description={"project_id": str(project.id), "trigger": "user"}
    )
    background_tasks.add_task(
        run_task_from_project,
        task_id=task.id,
        db_url=settings["db_url"],
        minio_settings={
            "endpoint": settings["minio_endpoint"],
            "access_key": settings["minio_access_key"],
            "secret_key": settings["minio_secret_key"],
            "bucket": settings["minio_bucket"],
            "secure": settings["minio_secure"]
        }
    )
    return {"task_id": task.id}

# --------------------- ЗАДАЧИ И РЕЗУЛЬТАТЫ ---------------------

@router.get("/task/{task_id}", response_model=schemas.TaskStatusResponse)
def get_task_status(
    task_id: uuid.UUID,
    user = Depends(get_current_user),
    task_repo = Depends(get_task_repo),
    result_repo = Depends(get_result_repo)
):
    task = task_repo.get_by_id(task_id)
    if not task or task.user_id != user["user_id"]:
        raise HTTPException(404, "Task not found")
    results = result_repo.get_by_task(task_id)
    results_info = [
        {
            "id": r.id,
            "result_type": r.result_type,
            "name": r.name,
            "data_url": r.data_url
        } for r in results
    ]
    return schemas.TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        created_at=task.created_at,
        finished_at=task.finished_at,
        error_message=task.error_message,
        results=results_info
    )

@router.get("/projects/{project_id}/results", response_model=List[schemas.ResultResponse])
def get_project_results(
    project_id: uuid.UUID,
    user = Depends(get_current_user),
    result_repo = Depends(get_result_repo)
):
    results = result_repo.get_by_project_and_user(project_id, user["user_id"])
    return [
        schemas.ResultResponse(
            id=r.id,
            task_id=r.task_id,
            result_type=r.result_type,
            name=r.name,
            data_url=r.data_url,
            created_at=r.created_at,
            geo_metadata=r.geo_metadata
        ) for r in results
    ]

@router.get("/results/{result_id}/download")
def download_result(
    result_id: uuid.UUID,
    user = Depends(get_current_user),
    result_repo = Depends(get_result_repo),
    settings = Depends(get_settings)
):
    result = result_repo.get_by_id(result_id)
    if not result or result.user_id != user["user_id"]:
        raise HTTPException(404)
    base_url = f"http://{settings['minio_public_host']}:9000/{settings['minio_bucket']}"
    preview_url = None
    if result.data_url.endswith('.tif'):
        preview_url = base_url + '/' + result.data_url.replace('.tif', '.png')
    return {
        "download_url": base_url + '/' + result.data_url,
        "preview_url": preview_url,
        "bbox": result.bbox
    }