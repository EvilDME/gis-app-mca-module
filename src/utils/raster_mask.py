import numpy as np
import pyproj
from shapely.ops import transform
from rasterio import features
from geoalchemy2.shape import to_shape
from src.core.models import RasterData

def reproject_polygon(polygon, src_crs='EPSG:4326', dst_crs='EPSG:32640'):
    """
    Перепроецирует полигон из src_crs в dst_crs.
    """
    project = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True).transform
    return transform(project, polygon)

def create_mask_from_polygon(study_area_wkb, transform, width, height, target_crs):
    """
    Создаёт бинарную маску (True внутри полигона) из WKB-геометрии.
    Полигон перепроецируется в целевую CRS растра.
    Если study_area_wkb None, возвращает маску из всех True.
    """
    if study_area_wkb is None:
        print("[create_mask] No study area, returning full True mask")
        return np.ones((height, width), dtype=bool)
    
    polygon = to_shape(study_area_wkb)
    print(f"[create_mask] Original polygon CRS: EPSG:4326, target CRS: {target_crs}")
    polygon_reproj = reproject_polygon(polygon, 'EPSG:4326', target_crs)
    print(f"[create_mask] Reprojected polygon bounds: {polygon_reproj.bounds}")
    
    # Растеризуем полигон: mask = True внутри полигона
    mask = features.geometry_mask(
        [polygon_reproj],
        out_shape=(height, width),
        transform=transform,
        invert=True   # True для пикселей внутри полигона
    )
    inside_count = np.sum(mask)
    print(f"[create_mask] Mask created: {inside_count} pixels inside ({(inside_count/(height*width))*100:.2f}%)")
    return mask

def apply_mask_to_raster(raster_data, mask, nodata_value=None):
    """
    Применяет маску к растру: значения вне маски заменяет на nodata.
    """
    values = raster_data.values.copy()
    nodata = nodata_value if nodata_value is not None else raster_data.meta.get('nodata')
    if nodata is None:
        nodata = -9999
    outside_count = np.sum(~mask)
    print(f"[apply_mask] Replacing {outside_count} pixels outside mask with nodata={nodata}")
    values[~mask] = nodata
    new_meta = raster_data.meta.copy()
    new_meta['nodata'] = nodata
    return RasterData(values=values, meta=new_meta, name=raster_data.name)