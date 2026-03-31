import rasterio
import pyproj
import os

print(f"--- Проверка окружения ---")
print(f"Python version: {os.sys.version}")

# Проверяем, не установлены ли глобальные переменные, которые могут всё испортить
for var in ['PROJ_LIB', 'PROJ_DATA', 'GDAL_DATA']:
    status = os.environ.get(var, 'Не установлена (это хорошо)')
    print(f"{var}: {status}")

try:
    # Проверка трансформации координат (использует proj.db)
    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857")
    point = transformer.transform(55.75, 37.61)
    print(f"PROJ Test: OK (Moscow in 3857: {point})")

    # Проверка Rasterio
    with rasterio.Env() as env:
        print(f"Rasterio GDAL version: {rasterio.__gdal_version__}")
        print("Rasterio Test: OK")

except Exception as e:
    print(f"\n--- ОШИБКА ---")
    print(e)