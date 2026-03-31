import numpy as np
import rasterio
from rasterio.transform import from_origin
import geopandas as gpd
from shapely.geometry import Point
import pyproj

def test_gis_stack():
    print("1. Тест Rasterio & Numpy: Создание маски высот...")
    # Создаем матрицу 10x10
    data = np.random.randint(0, 255, (10, 10)).astype('uint8')
    transform = from_origin(37.0, 55.0, 0.01, 0.01) # Координаты в районе Москвы
    
    with rasterio.open('test_temp.tif', 'w', driver='GTiff', height=10, width=10, 
                       count=1, dtype='uint8', crs='EPSG:4326', transform=transform) as dst:
        dst.write(data, 1)
    print("   - Растр успешно создан.")

    print("2. Тест Shapely & Pyproj: Геометрия и проекции...")
    # Создаем точку в WGS84
    msk_point = Point(37.6173, 55.7558)
    # Проектируем в Меркатор (метрическая система)
    wgs84 = pyproj.CRS('EPSG:4326')
    utm = pyproj.CRS('EPSG:3857')
    project = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
    point_utm = Point(project(msk_point.x, msk_point.y))
    print(f"   - Точка перепроецирована: {point_utm.x:.2f}, {point_utm.y:.2f}")

    print("3. Тест GeoPandas: Буфер и пересечение...")
    # Создаем буфер 500 метров вокруг точки
    gdf = gpd.GeoDataFrame([{'geometry': point_utm}], crs='EPSG:3857')
    buffer = gdf.buffer(500)
    print(f"   - Буфер создан. Площадь: {buffer.area.iloc[0]:.2f} м²")

    print("\nИТОГ: Все библиотеки работают корректно!")

if __name__ == "__main__":
    try:
        test_gis_stack()
    except Exception as e:
        print(f"\nОШИБКА: {e}")
    finally:
        import os
        if os.path.exists('test_temp.tif'):
            os.remove('test_temp.tif')