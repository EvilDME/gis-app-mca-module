import rasterio
from src.core.models import RasterData
from src.io.interfaces import BaseRasterWriter


class LocalRasterWriter(BaseRasterWriter):
    """Сохраняет растровые данные в локальный файл GeoTIFF."""
    
    def write_raster(self, raster: RasterData, destination: str) -> None:
        """
        Записывает растр в файл, используя метаданные из RasterData.
        
        Args:
            raster: Объект RasterData с данными и метаданными.
            destination: Путь для сохранения (например, output/result.tif).
        """
        if not destination:
            raise ValueError("Путь назначения не указан.")
        
        # Убедимся, что метаданные содержат необходимые ключи
        meta = raster.meta.copy()
        meta.update({
            'driver': 'GTiff',
            'count': 1,
            'dtype': raster.values.dtype
        })
        
        try:
            with rasterio.open(destination, 'w', **meta) as dst:
                dst.write(raster.values, 1)
        except Exception as e:
            raise RuntimeError(f"Ошибка записи растра в {destination}: {e}")