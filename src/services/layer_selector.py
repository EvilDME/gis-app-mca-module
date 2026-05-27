# src/services/layer_selector.py
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from geoalchemy2 import shape
from shapely.geometry import Polygon, shape as shapely_shape

from src.db.repositories import LayerRepository
from src.db.models import Layer

logger = logging.getLogger(__name__)


class LayerSelector:
    """Выбирает подходящие слои из БД для критериев анализа."""
    
    def __init__(self, session: Session):
        self.session = session
        self.layer_repo = LayerRepository(session)
    
    def select_for_slope(self) -> Optional[Layer]:
        """
        Выбирает растр для анализа уклона (slope).
        Приоритет:
        1. Растры с source_type='minio_raster' и supported_analyses содержит 'slope'
        2. С максимальным разрешением (минимальный resolution)
        """
        layers = self.layer_repo.list_by_supported_analysis('slope')
        layers = [l for l in layers if l.source_type == 'minio_raster']
        
        if not layers:
            logger.error("No raster layer found for slope analysis")
            return None
        
        # Сортируем по разрешению (меньше = детальнее)
        layers_sorted = sorted(layers, key=lambda x: x.resolution if x.resolution else float('inf'))
        selected = layers_sorted[0]
        logger.info(f"Selected layer for slope: {selected.name} (resolution: {selected.resolution})")
        return selected
    
    def select_for_proximity(self, study_area: Optional[Polygon] = None) -> Optional[Layer]:
        """
        Выбирает векторный слой для анализа близости (proximity).
        Приоритет:
        1. Векторы с source_type='postgis_vector' и supported_analyses содержит 'proximity'
        2. Если задана study_area, предпочтение слою с пересекающимся extent
        3. Иначе любой подходящий вектор
        """
        layers = self.layer_repo.list_by_supported_analysis('proximity')
        layers = [l for l in layers if l.source_type == 'postgis_vector']
        
        if not layers:
            logger.error("No vector layer found for proximity analysis")
            return None
        
        # Если есть область интереса, пытаемся найти пересекающиеся слои
        if study_area is not None:
            intersecting = []
            for layer in layers:
                if layer.extent is None:
                    continue
                # Преобразуем WKB элемента в Shapely-полигон
                extent_shape = shape.to_shape(layer.extent)
                if extent_shape.intersects(study_area):
                    intersecting.append(layer)
            
            if intersecting:
                selected = intersecting[0]  # Можно добавить более сложную логику
                logger.info(f"Selected layer for proximity (intersects study area): {selected.name}")
                return selected
        
        # Если нет пересечения или extent не задан, берём первый попавшийся
        selected = layers[0]
        logger.info(f"Selected layer for proximity: {selected.name}")
        return selected
    
    def select_for_reclass(self) -> Optional[Layer]:
        """
        Выбирает растр для переклассификации (reclass).
        Аналогично slope, но с supported_analyses содержит 'reclass'
        """
        layers = self.layer_repo.list_by_supported_analysis('reclass')
        layers = [l for l in layers if l.source_type == 'minio_raster']
        
        if not layers:
            logger.error("No raster layer found for reclass analysis")
            return None
        
        layers_sorted = sorted(layers, key=lambda x: x.resolution if x.resolution else float('inf'))
        selected = layers_sorted[0]
        logger.info(f"Selected layer for reclass: {selected.name}")
        return selected
    
    def select_by_analysis_type(self, analysis_type: str, study_area: Optional[Polygon] = None) -> Optional[Layer]:
        """
        Универсальный метод выбора слоя по типу анализа.
        """
        if analysis_type == 'slope':
            return self.select_for_slope()
        elif analysis_type == 'proximity':
            return self.select_for_proximity(study_area)
        elif analysis_type == 'reclass':
            return self.select_for_reclass()
        else:
            logger.error(f"Unknown analysis type: {analysis_type}")
            return None
    
    def get_master_layer(self, criteria_types: List[str]) -> Optional[Layer]:
        """
        Определяет мастер-сетку (эталонный растр) для выравнивания.
        Обычно это слой, используемый для slope, или первый попавшийся растр.
        """
        # Сначала ищем slope-слой
        for c_type in criteria_types:
            if c_type == 'slope':
                return self.select_for_slope()
        
        # Если slope нет, ищем любой растр
        layers = self.layer_repo.list_by_source_type('minio_raster')
        if layers:
            selected = layers[0]
            logger.info(f"No slope criterion, using raster as master: {selected.name}")
            return selected
        
        logger.error("No raster layer found for master grid")
        return None