from abc import ABC, abstractmethod
from src.core.models import RasterData

class BaseRasterReader(ABC):
    """Абстрактный класс. Мы не можем создать его экземпляр, 
    но мы обещаем, что у любого ридера будет метод read_raster."""
    
    @abstractmethod
    def read_raster(self, source: str) -> RasterData:
        pass