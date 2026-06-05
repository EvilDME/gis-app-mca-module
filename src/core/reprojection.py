import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from src.core.models import RasterData
import geopandas as gpd

def reproject_raster(raster: RasterData, target_crs: str = 'EPSG:32640') -> RasterData:
    """
    Перепроецирует RasterData, сохраняя оригинальные значения Nodata.
    """
    print(f"Репроецирование растра {raster.name} в {target_crs}")
    
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

def align_raster(target: RasterData, reference: RasterData) -> RasterData:
    """
    Приводит target к сетке reference (CRS, Transform, Width, Height).
    Это гарантирует, что массивы numpy будут идентичны по размеру.
    """
    # Если они уже идентичны, ничего не делаем (экономим время)
    if (target.meta['crs'] == reference.meta['crs'] and 
        target.meta['transform'] == reference.meta['transform'] and
        target.meta['width'] == reference.meta['width'] and
        target.meta['height'] == reference.meta['height']):
        return target

    print(f"📏 Выравнивание {target.name} под сетку {reference.name}...")

    # 1. Извлекаем параметры эталона
    dst_crs = reference.meta['crs']
    dst_transform = reference.meta['transform']
    dst_width = reference.meta['width']
    dst_height = reference.meta['height']
    dst_nodata = target.meta.get('nodata') # Сохраняем nodata из мишени

    # 2. Создаем пустой массив нужного размера (как у эталона)
    aligned_values = np.full(
        (dst_height, dst_width), 
        dst_nodata if dst_nodata is not None else np.nan, 
        dtype=target.values.dtype
    )

    # 3. Репроецируем / Пересчитываем сетку
    reproject(
        source=target.values,
        destination=aligned_values,
        src_transform=target.meta['transform'],
        src_crs=target.meta['crs'],
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=Resampling.bilinear, # Билинейная интерполяция лучше для непрерывных данных
        src_nodata=dst_nodata,
        dst_nodata=dst_nodata
    )

    # 4. Собираем новые метаданные
    new_meta = target.meta.copy()
    new_meta.update({
        'crs': dst_crs,
        'transform': dst_transform,
        'width': dst_width,
        'height': dst_height
    })

    return RasterData(
        values=aligned_values,
        meta=new_meta,
        name=f"{target.name}_aligned"
    )