from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class RasterData:
    """Универсальный объект растровых данных для нашего ядра."""
    values: np.ndarray      # Сама матрица (высоты, уклоны и т.д.)
    meta: dict              # Метаданные (CRS, transform, nodata)
    name: str               # Название слоя (например, 'elevation')