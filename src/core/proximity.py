import numpy as np
import rasterio.features
from scipy.ndimage import distance_transform_edt
from src.core.models import RasterData
import geopandas as gpd

def calculate_proximity(vector_data: gpd.GeoDataFrame, template_raster: RasterData) -> RasterData:
    """
    Рассчитывает евклидово расстояние от каждой ячейки растра до ближайшего векторного объекта.
    """
    print(f"Расчет расстояний")

    # 1. Проверяем проекции (критично!)
    if vector_data.crs != template_raster.meta['crs']:
        print(f"Перепроецирование векторов из {vector_data.crs} в {template_raster.meta['crs']}")
        vector_data = vector_data.to_crs(template_raster.meta['crs'])

    # 2. РАСТЕРИЗАЦИЯ (Создаем бинарную маску)
    # Все пиксели, где есть объект = 0, всё остальное = 1
    # Мы ставим 0 на объекты, потому что distance_transform_edt считает расстояние до НУЛЕЙ.
    
    width = template_raster.meta['width']
    height = template_raster.meta['height']
    transform = template_raster.meta['transform']

    # Генерируем список геометрий для rasterize
    shapes = vector_data.geometry

    # Создаем маску: 0 там где объекты, 1 там где пустота
    mask = rasterio.features.rasterize(
        shapes,
        out_shape=(height, width),
        transform=transform,
        fill=1,         # Пустота
        default_value=0 # Объекты
    )

    # 3. РАСЧЕТ РАССТОЯНИЙ (EDT)
    # Возвращает расстояние в пикселях
    distances_px = distance_transform_edt(mask)

    # 4. ПЕРЕВОД В МЕТРЫ
    # Умножаем расстояние в пикселях на размер пикселя (cell size)
    cell_size = abs(transform[0])
    distances_m = distances_px * cell_size

    # 5. СБОРКА РЕЗУЛЬТАТА
    new_meta = template_raster.meta.copy()
    new_meta.update({'dtype': 'float32', 'nodata': -9999})

    return RasterData(
        values=distances_m.astype(np.float32),
        meta=new_meta,
        name=f"proximity_to_{template_raster.name}"
    )