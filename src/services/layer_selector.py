# src/services/layer_selector.py
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from geoalchemy2 import shape
from shapely.geometry import Polygon

from src.db.repositories import LayerRepository
from src.db.models import Layer

logger = logging.getLogger(__name__)


class LayerSelector:
    """Выбирает подходящие слои из БД для критериев анализа."""

    def __init__(self, session: Session):
        self.session = session
        self.layer_repo = LayerRepository(session)

    def select_layer(
        self,
        analysis_type: str,
        data_type: str,
        study_area: Optional[Polygon] = None
    ) -> Optional[Layer]:
        """
        Выбирает слой по типу анализа и ожидаемому типу данных.
        Приоритет:
        1. Фильтр по supported_analyses (содержит analysis_type)
        2. Фильтр по source_type (minio_raster для slope/reclass, postgis_vector для proximity)
        3. Фильтр по data_type (обязательное точное совпадение)
        4. Если задана study_area, предпочтение слою с пересекающимся extent
        5. Для растров (slope/reclass) – с минимальным resolution (самый детальный)
        6. Для векторов – первый подходящий
        """
        # 1. Базовый фильтр по supported_analyses
        layers = self.layer_repo.list_by_supported_analysis(analysis_type)
        if not layers:
            logger.error(f"No layers support analysis type '{analysis_type}'")
            return None

        # 2. Фильтр по source_type
        if analysis_type in ('slope', 'reclass'):
            layers = [l for l in layers if l.source_type == 'minio_raster']
        elif analysis_type == 'proximity':
            layers = [l for l in layers if l.source_type == 'postgis_vector']
        else:
            logger.error(f"Unknown analysis type: {analysis_type}")
            return None

        if not layers:
            logger.error(f"No layers with source_type for '{analysis_type}'")
            return None

        # 3. Фильтр по data_type (точное совпадение)
        layers = [l for l in layers if l.data_type == data_type]
        if not layers:
            logger.error(f"No layer with data_type='{data_type}' for analysis '{analysis_type}'")
            return None

        # 4. Если есть study_area, пытаемся найти пересекающийся слой
        if study_area is not None:
            intersecting = []
            for layer in layers:
                if layer.extent is None:
                    continue
                extent_shape = shape.to_shape(layer.extent)
                if extent_shape.intersects(study_area):
                    intersecting.append(layer)
            if intersecting:
                selected = intersecting[0]
                logger.info(f"Selected intersecting layer for {analysis_type}/{data_type}: {selected.name}")
                return selected

        # 5. Для растров – сортировка по resolution (меньше = детальнее)
        if analysis_type in ('slope', 'reclass'):
            layers_sorted = sorted(layers, key=lambda x: x.resolution if x.resolution else float('inf'))
            selected = layers_sorted[0]
            logger.info(f"Selected raster layer for {analysis_type}/{data_type}: {selected.name} (resolution={selected.resolution})")
            return selected

        # 6. Для векторов – первый в списке
        selected = layers[0]
        logger.info(f"Selected vector layer for {analysis_type}/{data_type}: {selected.name}")
        return selected

    # Ниже приведены старые методы для обратной совместимости (могут быть удалены после рефакторинга)
    def select_for_slope(self) -> Optional[Layer]:
        return self.select_layer('slope', 'dem')

    def select_for_proximity(self, study_area: Optional[Polygon] = None) -> Optional[Layer]:
        # Здесь нужно знать, какой data_type ожидается – обычно для proximity ожидается 'roads' или 'water'
        # Этот метод устарел, используйте select_layer явно.
        logger.warning("select_for_proximity is deprecated, use select_layer with explicit data_type")
        return None

    def select_for_reclass(self) -> Optional[Layer]:
        return self.select_layer('reclass', 'landcover')

    def select_by_analysis_type(self, analysis_type: str, study_area: Optional[Polygon] = None) -> Optional[Layer]:
        # Устаревший метод – не используйте, он не учитывает data_type
        logger.warning("select_by_analysis_type is deprecated, use select_layer with explicit data_type")
        return None

    def get_master_layer(self, criteria_types: List[str]) -> Optional[Layer]:
        # Определяет мастер-сетку: слой с data_type='dem' и analysis_type='slope'
        return self.select_layer('slope', 'dem')