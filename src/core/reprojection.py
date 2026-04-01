import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from src.core.models import RasterData
import geopandas as gpd

def reproject_raster(raster: RasterData, target_crs: str = 'EPSG:32640') -> RasterData:
    """
    Перепроецирует RasterData, сохраняя оригинальные значения Nodata.
    """
    print(f"🔄 Репроецирование растра {raster.name} в {target_crs}...")
    
    src_crs = raster.meta['crs']
    width = raster.meta['width']
    height = raster.meta['height']
    transform = raster.meta['transform']
    nodata = raster.meta.get('nodata') # Получаем наш -9999 или другой nodata

    # 1. Рассчитываем новую сетку
    dst_transform, dst_width, dst_height = calculate_default_transform(
        src_crs, target_crs, width, height, *rasterio.transform.array_bounds(height, width, transform)
    )

    # 2. Инициализация массива значением NODATA вместо нулей
    # Если nodata не задан, используем np.nan (для float) или 0 как крайний случай
    fill_value = nodata if nodata is not None else np.nan
    dst_values = np.full((dst_height, dst_width), fill_value, dtype=raster.values.dtype)

    # 3. Выполняем перенос данных (Warp)
    reproject(
        source=raster.values,
        destination=dst_values,
        src_transform=transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=target_crs,
        resampling=Resampling.bilinear,
        src_nodata=nodata, # Явно указываем, что считать пустотой в источнике
        dst_nodata=nodata  # Явно указываем, чем забивать пустоту в результате
    )

    # 4. Обновляем метаданные
    new_meta = raster.meta.copy()
    new_meta.update({
        'crs': target_crs,
        'transform': dst_transform,
        'width': dst_width,
        'height': dst_height,
        'nodata': nodata # Сохраняем тот же nodata
    })

    return RasterData(
        values=dst_values,
        meta=new_meta,
        name=f"{raster.name}_reprojected"
    )

def reproject_vector(gdf: gpd.GeoDataFrame, target_crs: str = 'EPSG:32640') -> gpd.GeoDataFrame:
    """Перепроецирует GeoDataFrame."""
    if gdf.crs == target_crs:
        return gdf
    print(f"🔄 Репроецирование вектора в {target_crs}...")
    return gdf.to_crs(target_crs)