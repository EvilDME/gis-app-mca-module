import geopandas as gpd
from src.io.interfaces import BaseVectorReader


class LocalVectorReader(BaseVectorReader):
    """Читает векторные данные из локальных файлов (Shapefile, GeoJSON и др.)."""
    
    def read_vector(self, source: str) -> gpd.GeoDataFrame:
        """
        Загружает векторный слой с помощью geopandas.
        
        Args:
            source: Путь к файлу (например, data/roads.shp)
        
        Returns:
            GeoDataFrame с геометрией.
        """
        if not source:
            raise ValueError("Путь к векторному файлу не указан.")
        
        try:
            gdf = gpd.read_file(source)
        except Exception as e:
            raise RuntimeError(f"Ошибка чтения векторного файла {source}: {e}")
        
        return gdf