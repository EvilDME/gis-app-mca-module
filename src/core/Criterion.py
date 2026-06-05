import json
import numpy as np
from src.core.models import RasterData # Твоя модель данных

class Criterion:
    def __init__(self, id, display_name, points, weight=1.0):
        self.id = id
        self.display_name = display_name
        self.weight = weight
        points = sorted(points, key=lambda x: x[0])
        self.x_values = np.array([p[0] for p in points])
        self.y_values = np.array([p[1] for p in points])

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data['id'],
            display_name=data.get('display_name', data['id']),
            points=data['evaluation']['points'],
            weight=data.get('weight', 1.0)
        )
    
    def evaluate(self, raster: RasterData) -> RasterData:
        """Превращает сырые данные растра в оценки [0, 1] на основе точек."""
        print(f"Evaluating criteria {self.display_name}")
        print(f"Raster shape: {raster.values.shape}")
        
        values = raster.values.astype(np.float32)
        nodata = raster.meta.get('nodata')
        
        if nodata is not None:
            valid_mask = ~np.isclose(values, nodata)
        else:
            valid_mask = np.ones_like(values, dtype=bool)

        # Создаем массив для результата
        result = np.full_like(values, nodata if nodata is not None else np.nan)

        # Сама интерполяция (только для валидных пикселей)
        # np.interp(значения, x_точки, y_точки)
        # left/right параметры определяют, что будет за границами крайних точек
        result[valid_mask] = np.interp(
            values[valid_mask], 
            self.x_values, 
            self.y_values,
            left=self.y_values[0], 
            right=self.y_values[-1]
        )

        new_meta = raster.meta.copy()
        new_meta.update({'dtype': np.float32})
        
        print("Interpolation finished")
        
        return RasterData(values=result.astype(np.float32), meta=new_meta, name=f"{self.id}_scored")