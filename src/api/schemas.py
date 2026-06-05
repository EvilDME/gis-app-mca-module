from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

# GeoJSON Geometry (упрощённо для Study Area)
GeoJSONPolygon = Dict[str, Any]  # {"type": "Polygon", "coordinates": [...]}

# --------------------- ЗАПРОСЫ ---------------------
class CriterionRequest(BaseModel):
    """Критерий в запросе на анализ (без указания source)."""
    id: str
    type: str  # 'slope', 'proximity', 'reclass'
    evaluation: Dict[str, Any]  # содержит "points": [[0,1], ...]

class AggregationConfig(BaseModel):
    method: str  # 'weighted_sum' или 'geometric_mean'
    weights: Dict[str, float]  # ключ - id критерия, значение - вес

class AnalysisRequest(BaseModel):
    """Запрос на анализ от клиента (без source)."""
    user_id: str
    project_name: str
    study_area: GeoJSONPolygon
    aggregation: AggregationConfig
    criteria: List[CriterionRequest]

# --------------------- ПРОЕКТЫ ---------------------
class ProjectCreateRequest(BaseModel):
    name: str
    study_area: GeoJSONPolygon
    aggregation_method: str

class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    study_area: Optional[GeoJSONPolygon] = None
    aggregation_method: Optional[str] = None

class ProjectResponse(BaseModel):
    id: UUID
    name: str
    user_id: str
    aggregation_method: str
    study_area: Optional[GeoJSONPolygon] = None
    created_at: datetime
    updated_at: datetime

# --------------------- КРИТЕРИИ ---------------------
class CriterionCreateRequest(BaseModel):
    analysis_type: str
    weight: float = Field(..., ge=0, le=1)
    logic_params: Dict[str, Any]

class CriterionUpdateRequest(BaseModel):
    weight: Optional[float] = Field(None, ge=0, le=1)
    logic_params: Optional[Dict[str, Any]] = None

class CriterionResponse(BaseModel):
    id: UUID
    project_id: UUID
    analysis_type: str
    weight: float
    logic_params: Dict[str, Any]
    created_at: datetime

# --------------------- ЗАДАЧИ И РЕЗУЛЬТАТЫ ---------------------
class TaskStatusResponse(BaseModel):
    task_id: UUID
    status: str  # PENDING, PROCESSING, COMPLETED, FAILED
    created_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results: List[Dict[str, Any]] = []  # список с id, result_type, name, data_url

class ResultResponse(BaseModel):
    id: UUID
    task_id: UUID
    result_type: str
    name: str
    data_url: str
    created_at: datetime
    geo_metadata: Optional[Dict[str, Any]] = None
    
# --------------------- ПРОЕКТЫ С КРИТЕРИЯМИ ---------------------
class CriterionCreateRequest(BaseModel):
    analysis_type: str
    weight: float = Field(..., ge=0, le=1)
    logic_params: Dict[str, Any]

class ProjectWithCriteriaCreateRequest(BaseModel):
    name: str
    study_area: GeoJSONPolygon
    aggregation_method: str
    criteria: List[CriterionCreateRequest]

class CriterionResponseFull(BaseModel):
    id: UUID
    analysis_type: str
    weight: float
    logic_params: Dict[str, Any]
    created_at: datetime

class ProjectWithCriteriaResponse(BaseModel):
    id: UUID
    name: str
    user_id: str
    aggregation_method: str
    study_area: Optional[GeoJSONPolygon] = None
    created_at: datetime
    updated_at: datetime
    criteria: List[CriterionResponse]