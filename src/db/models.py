import uuid
import datetime
from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Enum, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from geoalchemy2 import Geometry

Base = declarative_base()


class Layer(Base):
    """Каталог доступных исходных слоёв (растры в MinIO или векторы в PostGIS)."""
    __tablename__ = 'layers'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    source_type = Column(Enum('minio_raster', 'postgis_vector', name='source_type_enum'), nullable=False)
    data_path = Column(String, nullable=False)          # bucket/key или schema.table
    geometry_type = Column(String(50), nullable=True)   # Polygon, LineString, Point (только векторы)
    crs = Column(String(20), nullable=False)            # EPSG:xxxx
    extent = Column(Geometry('POLYGON', srid=4326))     # охват в WGS84
    resolution = Column(Float, nullable=True)           # размер ячейки (м), только для растров
    supported_analyses = Column(JSONB, nullable=False, default=list)  # например ["slope","reclass"] или ["proximity"]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    data_type = Column(String(50), nullable=False)

class McaProject(Base):
    """Проект пользователя – задаёт область интереса, метод агрегации, но не содержит результатов."""
    __tablename__ = 'mca_projects'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False)          # идентификатор из внешней системы
    name = Column(String(255), nullable=False)
    study_area = Column(Geometry('POLYGON', srid=4326))    # область интереса
    aggregation_method = Column(Enum('weighted_sum', 'geometric_mean', name='agg_method_enum'), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # связи
    criteria = relationship("ProjectCriterion", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="project", cascade="all, delete-orphan")


class ProjectCriterion(Base):
    """Критерий внутри проекта – какой слой, вес, тип обработки и параметры."""
    __tablename__ = 'project_criteria'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('mca_projects.id', ondelete='CASCADE'))
    weight = Column(Float, nullable=False)               # от 0 до 1
    analysis_type = Column(Enum('slope', 'proximity', 'reclass', name='analysis_type_enum'), nullable=False)
    data_type = Column(String(50), nullable=False)
    logic_params = Column(JSONB, nullable=False)         # например {"units":"degrees"} или {"normalization_points":[[0,1],[500,0]]}
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # связи
    project = relationship("McaProject", back_populates="criteria")
    results = relationship("Result", back_populates="criterion")


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('mca_projects.id', ondelete='CASCADE'))
    user_id = Column(String(255), nullable=False)
    external_id = Column(String(255), unique=True, nullable=True)  # добавлено
    status = Column(Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='task_status_enum'), nullable=False, default='PENDING')
    description = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)

    # связи
    project = relationship("McaProject", back_populates="tasks")
    results = relationship("Result", back_populates="task", cascade="all, delete-orphan")


class Result(Base):
    __tablename__ = 'results'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('tasks.id', ondelete='CASCADE'))
    project_id = Column(UUID(as_uuid=True), ForeignKey('mca_projects.id', ondelete='CASCADE'))
    user_id = Column(String(255), nullable=False)  # ← добавить
    criterion_id = Column(UUID(as_uuid=True), ForeignKey('project_criteria.id', ondelete='SET NULL'), nullable=True)
    result_type = Column(Enum('intermediate_raster', 'final_raster', 'vector_output', name='result_type_enum'), nullable=False)
    data_url = Column(String, nullable=False)
    geo_metadata = Column(JSONB, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    bbox = Column(JSONB, nullable=True)

    # связи
    task = relationship("Task", back_populates="results")
    project = relationship("McaProject", back_populates="results")
    criterion = relationship("ProjectCriterion", back_populates="results")