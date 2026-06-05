import uuid
import numpy as np
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from shapely.geometry import shape as shapely_shape
from geoalchemy2 import shape as geoalchemy_shape

from src.core.models import RasterData
from src.core.Criterion import Criterion
from src.core.terrain import calculate_slope
from src.core.proximity import calculate_proximity
from src.core.reprojection import reproject_raster, align_raster
from src.core.mce import sum_weights, geometric_mean_weights
from src.db.repositories import (
    LayerRepository, McaProjectRepository,
    TaskRepository, ResultRepository, ProjectCriterionRepository
)
from src.services.layer_selector import LayerSelector


class McaOrchestrator:
    def __init__(
        self,
        session: Session,
        layer_repo: LayerRepository,
        project_repo: McaProjectRepository,
        task_repo: TaskRepository,
        result_repo: ResultRepository,
        criterion_repo: ProjectCriterionRepository,
        raster_reader,
        vector_reader,
        raster_writer
    ):
        self.session = session
        self.layer_repo = layer_repo
        self.project_repo = project_repo
        self.task_repo = task_repo
        self.result_repo = result_repo
        self.criterion_repo = criterion_repo
        self.raster_reader = raster_reader
        self.vector_reader = vector_reader
        self.raster_writer = raster_writer
        self.layer_selector = LayerSelector(session)

    def run_from_project(self, task_id: uuid.UUID):
        print(f"Starting analysis for task {task_id} from project")

        task = self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        project = self.project_repo.get_by_id(task.project_id, load_criteria=True)
        if not project:
            raise ValueError(f"Project {task.project_id} not found")

        user_id = project.user_id
        criteria = project.criteria
        if not criteria:
            raise ValueError("Project has no criteria")

        selected_layers = {}
        study_area_shape = None
        if project.study_area:
            study_area_shape = geoalchemy_shape.to_shape(project.study_area)

        for crit in criteria:
            layer = self.layer_selector.select_by_analysis_type(
                crit.analysis_type,
                study_area=study_area_shape
            )
            if not layer:
                raise ValueError(f"No suitable layer for analysis type {crit.analysis_type}")
            selected_layers[crit.id] = layer
            print(f"Criterion {crit.id} uses layer {layer.name} ({layer.data_path})")

        master_criterion = None
        master_layer = None
        for crit in criteria:
            if crit.analysis_type == 'slope':
                master_criterion = crit
                master_layer = selected_layers[crit.id]
                break
        if not master_layer:
            raise ValueError("No slope criterion found – cannot determine master grid")

        master_raster = self.raster_reader.read_raster(master_layer.data_path)
        target_crs = "EPSG:32640"
        if master_raster.meta['crs'].is_geographic:
            master_raster = reproject_raster(master_raster, target_crs=target_crs)

        processed_factors = []

        for crit in criteria:
            layer = selected_layers[crit.id]
            print(f"Processing criterion {crit.id} ({crit.analysis_type})")

            if layer.source_type == 'minio_raster':
                raw_raster = self.raster_reader.read_raster(layer.data_path)
                if crit.analysis_type == 'slope':
                    if raw_raster.meta['crs'].is_geographic:
                        raw_raster = reproject_raster(raw_raster, target_crs=target_crs)
                    raw_raster = calculate_slope(raw_raster)
            elif layer.source_type == 'postgis_vector':
                if crit.analysis_type == 'proximity':
                    gdf = self.vector_reader.read_vector(layer.data_path)
                    raw_raster = calculate_proximity(gdf, master_raster)
                else:
                    raise ValueError(f"Vector layer cannot be used for {crit.analysis_type}")
            else:
                raise ValueError(f"Unknown source_type {layer.source_type}")

            aligned = align_raster(raw_raster, master_raster)

            crit_dict = {
                "id": str(crit.id),
                "display_name": layer.name,
                "type": crit.analysis_type,
                "evaluation": crit.logic_params.get('evaluation', {'points': [[0,1],[1,0]]}),
                "weight": crit.weight
            }
            criterion_logic = Criterion.from_dict(crit_dict)
            scored = criterion_logic.evaluate(aligned)
            scored_with_name = RasterData(values=scored.values, meta=scored.meta, name=f"{layer.name}_scored")
            processed_factors.append(scored_with_name)

            intermediate_key = f"users/{user_id}/projects/{project.id}/tasks/{task_id}/criteria/{crit.id}.tif"
            self.raster_writer.write_raster(scored, intermediate_key)
            self.result_repo.create(
                task_id=task_id,
                project_id=project.id,
                user_id=user_id,
                result_type="intermediate_raster",
                data_url=intermediate_key,
                name=f"Normalized {layer.name}",
                geo_metadata=self._extract_metadata(scored),
                criterion_id=crit.id
            )

        weights = {str(c.id): c.weight for c in criteria}
        if project.aggregation_method == "weighted_sum":
            final_raster = sum_weights(processed_factors, weights)
        elif project.aggregation_method == "geometric_mean":
            final_raster = geometric_mean_weights(processed_factors, weights)
        else:
            raise ValueError(f"Unknown aggregation method {project.aggregation_method}")

        final_key = f"users/{user_id}/projects/{project.id}/tasks/{task_id}/final.tif"
        self.raster_writer.write_raster(final_raster, final_key)
        self.result_repo.create(
            task_id=task_id,
            project_id=project.id,
            user_id=user_id,
            result_type="final_raster",
            data_url=final_key,
            name=f"Final suitability for {project.name}",
            geo_metadata=self._extract_metadata(final_raster),
            criterion_id=None
        )
        self.task_repo.update_status(task.id, "COMPLETED")
        
        print(f"Analysis completed. Task {task_id} finished.")

    def _extract_metadata(self, raster: RasterData) -> Dict[str, Any]:
        return {
            "crs": str(raster.meta.get('crs')),
            "dtype": str(raster.values.dtype),
            "min": float(np.nanmin(raster.values)),
            "max": float(np.nanmax(raster.values)),
            "nodata": raster.meta.get('nodata')
        }