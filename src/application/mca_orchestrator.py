import os
import json
import numpy as np
from src.core.models import RasterData 
from src.core.Criterion import Criterion
from src.core.terrain import calculate_slope
from src.core.proximity import calculate_proximity
from src.core.reprojection import reproject_raster, align_raster
from src.core.mce import sum_weights, geometric_mean_weights

class McaOrchestrator:
    def __init__(self, r_reader, v_reader, writer):
        self.r_reader = r_reader
        self.v_reader = v_reader
        self.writer = writer

    def run_project(self, project_path: str):
        """Полный запуск проекта на основе JSON-спецификации."""
        print(f"🌟 Запуск проекта: {project_path}")
        
        # 1. Загрузка и проверка контракта
        with open(project_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        env = config['environment']
        agg = config['aggregation']
        output_dir = env['output_dir']
        os.makedirs(output_dir, exist_ok=True)

        # 2. Инициализация Master Grid (Эталонная сетка)
        print("🏗 Подготовка эталонной сетки...")
        master = self.r_reader.read_raster(env['master_grid'])
        if master.meta['crs'].is_geographic:
            master = reproject_raster(master, target_crs=env['target_crs'])
        
        processed_factors = []

        # 3. Цикл обработки каждого критерия
        for crit_config in config['criteria']:
            crit_id = crit_config['id']
            print(f"\n🛠 Обработка критерия: {crit_id} ({crit_config['type']})")
            
            # А. Расчет "сырых" данных
            raw_raster = self._calculate_raw_factor(crit_config, master)
            
            # Б. Выравнивание под Master Grid (Extent, Resolution, CRS)
            aligned = align_raster(raw_raster, master)
            
            # В. Оценка (Нормализация 0..1)
            # Передаем настройки интерполяции в объект Criterion
            criterion_logic = Criterion.from_dict(crit_config) 
            scored = criterion_logic.evaluate(aligned)
            
            # Присваиваем имя для MCE
            scored = RasterData(values=scored.values, meta=scored.meta, name=crit_id)
            processed_factors.append(scored)

            # Г. Сохранение промежуточных слоев (если включено)
            if env.get('save_intermediate', True):
                self.writer.write_raster(scored, os.path.join(output_dir, f"{crit_id}_scored.tif"))

        # 4. Финальная агрегация (MCE)
        print(f"\n⚖️ Агрегация методом: {agg['method']}")
        weights = agg['weights_config']
        
        if agg['method'] == "weighted_sum":
            final_raster = sum_weights(processed_factors, weights)
        elif agg['method'] == "geometric_mean":
            final_raster = geometric_mean_weights(processed_factors, weights)
        else:
            raise ValueError(f"Неизвестный метод агрегации: {agg['method']}")

        # 5. Сохранение результата
        final_path = os.path.join(output_dir, "FINAL_SUITABILITY.tif")
        self.writer.write_raster(final_raster, final_path)
        
        print(f"\n✅ Проект завершен успешно! Результат в: {final_path}")

    def _calculate_raw_factor(self, config, master) -> RasterData:
        """Вспомогательный метод для выбора математического модуля."""
        c_type = config['type']
        source = config['source']

        if c_type == "slope":
            # Для уклона читаем растр (обычно тот же DEM)
            raster = self.r_reader.read_raster(source)
            # Если DEM в градусах, репроецируем перед расчетом уклона
            if raster.meta['crs'].is_geographic:
                raster = reproject_raster(raster)
            return calculate_slope(raster)

        elif c_type == "proximity":
            # Для дистанции ищем .shp в папке или читаем файл
            if os.path.isdir(source):
                shp = [f for f in os.listdir(source) if f.endswith('.shp')][0]
                source = os.path.join(source, shp)
            vector = self.v_reader.read_vector(source)
            return calculate_proximity(vector, master)

        else:
            raise ValueError(f"Тип критерия {c_type} не поддерживается")