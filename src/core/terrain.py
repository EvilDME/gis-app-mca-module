import numpy as np
from scipy.ndimage import sobel, binary_erosion
from src.core.models import RasterData

def calculate_slope(dem: RasterData, units: str = "degrees") -> RasterData:
    values = dem.values.astype(np.float32)
    meta = dem.meta.copy()
    nodata = meta.get('nodata')

    # 1. Маска валидных данных
    if nodata is not None:
        valid_mask = ~np.isclose(values, nodata)
    else:
        valid_mask = np.ones_like(values, dtype=bool)

    # --- СЕКРЕТ ARCGIS: ЭРОЗИЯ МАСКИ ---
    # Мы помечаем как "невалидные" все пиксели, у которых нет полного окружения 3x3.
    # Это уберет артефакты в 90 градусов на краях.
    eroded_mask = binary_erosion(valid_mask, structure=np.ones((3, 3)))

    # Заполняем рабочую копию средним, чтобы Sobel не сходил с ума на краях,
    # но результат в этих пикселях мы всё равно затрем Nodata в конце.
    work_values = values.copy()
    if nodata is not None and np.any(valid_mask):
        mean_height = np.mean(values[valid_mask])
        work_values[~valid_mask] = mean_height

    # 2. Геометрия
    transform = meta.get('transform')
    cell_size_x = abs(transform[0])
    cell_size_y = abs(transform[4])

    # 3. Расчет производных
    dx = sobel(work_values, axis=1, mode='nearest') / (8 * cell_size_x)
    dy = sobel(work_values, axis=0, mode='nearest') / (8 * cell_size_y)
    rise_run = np.sqrt(dx**2 + dy**2)

    # 4. Финальный расчет
    if units == "degrees":
        result_array = np.degrees(np.arctan(rise_run))
    else:
        result_array = rise_run * 100

    # 5. ПРИМЕНЯЕМ ЭРОЗИРОВАННУЮ МАСКУ (Как в ArcGIS)
    # Используем eroded_mask: пиксели на самом краю станут Nodata
    final_values = np.full_like(values, nodata if nodata is not None else np.nan)
    final_values[eroded_mask] = result_array[eroded_mask]

    new_meta = meta.copy()
    new_meta.update({'dtype': np.float32})

    return RasterData(
        values=final_values.astype(np.float32),
        meta=new_meta,
        name=f"{dem.name}_slope"
    )