import rasterio
import os
from src.core.models import RasterData
from src.io.interfaces import BaseRasterReader

class LocalRasterReader(BaseRasterReader):
    """Реализация ридера для чтения GeoTIFF файлов с локального диска."""

    def read_raster(self, source: str) -> RasterData:
        """
        Читает растровый файл.
        
        Args:
            source: Путь к файлу на диске.
        Returns:
            Объект RasterData.
        """
        if not os.path.exists(source):
            raise FileNotFoundError(f"Файл не найден: {source}")

        try:
            with rasterio.open(source) as src:
                # Читаем первый слой
                values = src.read(1)
                # Копируем метаданные
                meta = src.profile.copy()
                # Имя слоя — это имя файла без расширения
                name = os.path.splitext(os.path.basename(source))[0]
                
                return RasterData(
                    values=values,
                    meta=meta,
                    name=name
                )
        except Exception as e:
            raise RuntimeError(f"Ошибка при чтении растра {source}: {e}")