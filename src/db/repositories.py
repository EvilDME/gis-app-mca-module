# src/db/repositories.py
import uuid
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from src.db.models import Layer, McaProject, ProjectCriterion, Task, Result, Base
from datetime import datetime


class BaseRepository:
    """Общий репозиторий с базовыми CRUD операциями."""
    def __init__(self, session: Session):
        self.session = session

    def add(self, entity):
        self.session.add(entity)
        return entity

    def delete(self, entity):
        self.session.delete(entity)

    def flush(self):
        self.session.flush()


class LayerRepository(BaseRepository):
    """Репозиторий для работы со слоями (исходные данные)."""
    
    def get_by_id(self, layer_id: uuid.UUID) -> Optional[Layer]:
        return self.session.query(Layer).filter(Layer.id == layer_id).first()

    def get_by_name(self, name: str) -> Optional[Layer]:
        return self.session.query(Layer).filter(Layer.name == name).first()

    def get_by_data_path(self, data_path: str) -> Optional[Layer]:
        return self.session.query(Layer).filter(Layer.data_path == data_path).first()

    def list_all(self) -> List[Layer]:
        return self.session.query(Layer).all()

    def list_by_source_type(self, source_type: str) -> List[Layer]:
        return self.session.query(Layer).filter(Layer.source_type == source_type).all()

    def list_by_supported_analysis(self, analysis_type: str) -> List[Layer]:
        """Возвращает слои, которые поддерживают указанный тип анализа (например, 'slope')."""
        # supported_analyses хранится как JSONB, используем contains
        return self.session.query(Layer).filter(Layer.supported_analyses.contains([analysis_type])).all()

    def create(self, name, source_type, data_path, crs, data_type, geometry_type=None, extent=None, resolution=None, supported_analyses=None):
        layer = Layer(
            name=name,
            source_type=source_type,
            data_path=data_path,
            geometry_type=geometry_type,
            crs=crs,
            data_type=data_type,
            extent=extent,
            resolution=resolution,
            supported_analyses=supported_analyses or []
        )
        self.add(layer)
        self.session.commit()
        return layer


class McaProjectRepository(BaseRepository):
    """Репозиторий для проектов MCA."""
    
    def get_by_id(self, project_id: uuid.UUID, load_criteria: bool = True) -> Optional[McaProject]:
        query = self.session.query(McaProject)
        if load_criteria:
            query = query.options(joinedload(McaProject.criteria))
        return query.filter(McaProject.id == project_id).first()

    def get_by_user(self, user_id: str) -> List[McaProject]:
        return self.session.query(McaProject).filter(McaProject.user_id == user_id).all()

    def list_all(self) -> List[McaProject]:
        return self.session.query(McaProject).all()

    def create(self, user_id: str, name: str, aggregation_method: str,
               study_area=None) -> McaProject:
        project = McaProject(
            user_id=user_id,
            name=name,
            aggregation_method=aggregation_method,
            study_area=study_area
        )
        self.add(project)
        self.session.commit()
        return project

    def update(self, project_id: uuid.UUID, **kwargs) -> Optional[McaProject]:
        project = self.get_by_id(project_id, load_criteria=False)
        if not project:
            return None
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        project.updated_at = datetime.utcnow()
        self.session.commit()
        return project

    def delete(self, project_id: uuid.UUID) -> bool:
        project = self.get_by_id(project_id, load_criteria=False)
        if not project:
            return False
        self.session.delete(project)
        self.session.commit()
        return True


class ProjectCriterionRepository(BaseRepository):
    """Репозиторий для критериев внутри проекта."""
    
    def get_by_id(self, criterion_id: uuid.UUID) -> Optional[ProjectCriterion]:
        return self.session.query(ProjectCriterion).filter(ProjectCriterion.id == criterion_id).first()

    def get_by_project(self, project_id: uuid.UUID) -> List[ProjectCriterion]:
        return self.session.query(ProjectCriterion).filter(ProjectCriterion.project_id == project_id).all()

    def create(self, project_id, weight, analysis_type, data_type, logic_params):
        criterion = ProjectCriterion(
            project_id=project_id,
            weight=weight,
            analysis_type=analysis_type,
            data_type=data_type,
            logic_params=logic_params
        )
        self.add(criterion)
        self.session.commit()
        return criterion

    def update(self, criterion_id: uuid.UUID, **kwargs) -> Optional[ProjectCriterion]:
        criterion = self.get_by_id(criterion_id)
        if not criterion:
            return None
        for key, value in kwargs.items():
            if hasattr(criterion, key):
                setattr(criterion, key, value)
        self.session.commit()
        return criterion

    def delete(self, criterion_id: uuid.UUID) -> bool:
        """Удаляет критерий по ID."""
        criterion = self.get_by_id(criterion_id)
        if not criterion:
            return False
        self.session.delete(criterion)
        self.session.commit()
        return True

    def delete_by_project(self, project_id: uuid.UUID) -> int:
        """Удаляет все критерии проекта. Возвращает количество удалённых."""
        deleted = self.session.query(ProjectCriterion).filter(ProjectCriterion.project_id == project_id).delete()
        self.session.commit()
        return deleted


    def create_with_external_id(self, project_id: uuid.UUID, user_id: str, external_id: str, description: Dict[str, Any]) -> Task:
        """Создаёт задачу с указанным external_id (строковый идентификатор от клиента)."""
        task = Task(
            project_id=project_id,
            user_id=user_id,
            external_id=external_id,
            description=description
        )
        self.add(task)
        self.session.commit()
        return task

    def get_by_external_id(self, external_id: str) -> Optional[Task]:
        """Находит задачу по внешнему строковому идентификатору."""
        return self.session.query(Task).filter(Task.external_id == external_id).first()

class TaskRepository(BaseRepository):
    """Репозиторий для задач (запусков проектов)."""
    
    def get_by_id(self, task_id: uuid.UUID) -> Optional[Task]:
        return self.session.query(Task).filter(Task.id == task_id).first()

    def get_by_project(self, project_id: uuid.UUID) -> List[Task]:
        return self.session.query(Task).filter(Task.project_id == project_id).order_by(Task.created_at.desc()).all()

    def create(self, project_id: uuid.UUID, user_id: str, description: Dict[str, Any]) -> Task:
        task = Task(
            project_id=project_id,
            user_id=user_id,
            description=description
        )
        self.add(task)
        self.session.commit()
        return task

    def create_with_external_id(self, project_id: uuid.UUID, user_id: str, external_id: str, description: Dict[str, Any]) -> Task:
        task = Task(
            project_id=project_id,
            user_id=user_id,
            external_id=external_id,
            description=description
        )
        self.add(task)
        self.session.commit()
        return task

    def update_status(self, task_id: uuid.UUID, status: str, error_message: Optional[str] = None) -> Optional[Task]:
        task = self.get_by_id(task_id)
        if not task:
            return None
        task.status = status
        if status in ('COMPLETED', 'FAILED'):
            task.finished_at = datetime.utcnow()
        if error_message:
            task.error_message = error_message
        self.session.commit()
        return task
    
    def get_by_user(self, user_id: str, limit: int = 100) -> List[Task]:
        return self.session.query(Task).filter(Task.user_id == user_id).order_by(Task.created_at.desc()).limit(limit).all()

    def get_by_user_and_status(self, user_id: str, status: str) -> List[Task]:
        return self.session.query(Task).filter(Task.user_id == user_id, Task.status == status).order_by(Task.created_at.desc()).all()

    def get_by_external_id(self, external_id: str) -> Optional[Task]:
        return self.session.query(Task).filter(Task.external_id == external_id).first()

class ResultRepository(BaseRepository):
    """Репозиторий для выходных результатов."""
    
    def get_by_id(self, result_id: uuid.UUID) -> Optional[Result]:
        return self.session.query(Result).filter(Result.id == result_id).first()

    def get_by_task(self, task_id: uuid.UUID) -> List[Result]:
        return self.session.query(Result).filter(Result.task_id == task_id).all()

    def get_by_project(self, project_id: uuid.UUID) -> List[Result]:
        return self.session.query(Result).filter(Result.project_id == project_id).all()

    def create(self, task_id: uuid.UUID, project_id: uuid.UUID, user_id: str,
            result_type: str, data_url: str, name: str,
            geo_metadata: Dict[str, Any],
            bbox: Optional[List[float]] = None,
            criterion_id: Optional[uuid.UUID] = None) -> Result:
        result = Result(
            task_id=task_id,
            project_id=project_id,
            user_id=user_id,
            criterion_id=criterion_id,
            result_type=result_type,
            data_url=data_url,
            geo_metadata=geo_metadata,
            name=name,
            bbox=bbox
        )
        self.add(result)
        self.session.commit()
        return result

    def delete_old(self, older_than_days: int = 30) -> int:
        """Удаляет результаты, созданные ранее указанного количества дней."""
        threshold = datetime.utcnow() - datetime.timedelta(days=older_than_days)
        deleted = self.session.query(Result).filter(Result.created_at < threshold).delete()
        self.session.commit()
        return deleted
    
    def get_by_user(self, user_id: str, limit: int = 100) -> List[Result]:
        """
        Возвращает все результаты пользователя, отсортированные по убыванию даты создания.
        """
        return self.session.query(Result).filter(Result.user_id == user_id).order_by(Result.created_at.desc()).limit(limit).all()

    def get_by_user_and_type(self, user_id: str, result_type: str) -> List[Result]:
        """
        Возвращает результаты пользователя определённого типа (intermediate_raster, final_raster, vector_output).
        """
        return self.session.query(Result).filter(Result.user_id == user_id, Result.result_type == result_type).order_by(Result.created_at.desc()).all()

    def get_by_project_and_user(self, project_id: uuid.UUID, user_id: str) -> List[Result]:
        """
        Возвращает результаты конкретного проекта с проверкой принадлежности пользователю.
        """
        return self.session.query(Result).filter(Result.project_id == project_id, Result.user_id == user_id).all()