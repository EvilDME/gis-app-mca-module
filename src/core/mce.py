import numpy as np
from src.core.models import RasterData
from typing import List, Dict

def _prepare_mce(rasters: List[RasterData], weights: Dict[str, float]):
    """Вспомогательная функция для проверки данных и подготовки маски Nodata."""
    reference = rasters[0]
    shape = reference.values.shape
    nodata = reference.meta.get('nodata')
    
    final_mask = np.ones(shape, dtype=bool)
    for raster in rasters:
        if nodata is not None:
            final_mask &= ~np.isclose(raster.values, nodata)
            
    return reference, shape, nodata, final_mask

def sum_weights(rasters: List[RasterData], weights: Dict[str, float]) -> RasterData:
    """Взвешенная линейная комбинация (аддитивная модель)."""
    print("Выполнение взвешенной суммы критериев")
    reference, shape, nodata, final_mask = _prepare_mce(rasters, weights)
    result_values = np.zeros(shape, dtype=np.float32)

    for raster in rasters:
        weight = weights.get(raster.name, 0.0)
        print(f"Критерий '{raster.name}': вес = {weight}")
        result_values += (raster.values * weight)

    if nodata is not None:
        result_values[~final_mask] = nodata

    print("Взвешенная сумма завершена")
    return RasterData(values=result_values, meta=reference.meta, name="mce_sum")

def geometric_mean_weights(rasters: List[RasterData], weights: Dict[str, float]) -> RasterData:
    """
    Взвешенное среднее геометрическое (мультипликативная модель).
    Формула: Product(factor_i ^ weight_i). Любой 0 обнуляет весь результат.
    """
    print("Выполнение взвешенного среднего геометрического")
    reference, shape, nodata, final_mask = _prepare_mce(rasters, weights)
    
    result_values = np.ones(shape, dtype=np.float32)

    for raster in rasters:
        weight = weights.get(raster.name, 0.0)
        print(f"Критерий '{raster.name}': вес = {weight}")
        result_values *= np.power(raster.values.astype(np.float32), weight)

    if nodata is not None:
        result_values[~final_mask] = nodata

    print("Взвешенное среднее геометрическое завершено")
    return RasterData(values=result_values, meta=reference.meta, name="mce_geometric")