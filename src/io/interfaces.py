from abc import ABC, abstractmethod
from typing import Any, Union

import geopandas as gpd
from src.core.models import RasterData


class BaseRasterReader(ABC):
    """Абстрактный класс для чтения растровых данных."""
    
    @abstractmethod
    def read_raster(self, source: str) -> RasterData:
        """Читает растр из указанного источника и возвращает RasterData."""
        pass


class BaseVectorReader(ABC):
    """Абстрактный класс для чтения векторных данных."""
    
    @abstractmethod
    def read_vector(self, source: str) -> gpd.GeoDataFrame:
        """
        Читает векторные данные из указанного источника.
        Возвращает GeoDataFrame (геопандас) с геометрией в исходной CRS.
        """
        pass


class BaseRasterWriter(ABC):
    """Абстрактный класс для записи растровых данных."""
    
    @abstractmethod
    def write_raster(self, raster: RasterData, destination: str) -> None:
        """Сохраняет растровые данные в указанное место."""
        pass