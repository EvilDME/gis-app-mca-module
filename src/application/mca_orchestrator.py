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
        self.r_reader = r_reader   # MinIORasterReader
        self.v_reader = v_reader   # PostGISVectorReader
        self.writer = writer       # MinIORasterWriter

    def run_project(self, project_path: str):
        print(f"🌟 Запуск проекта: {project_path}")
        with open(project_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        env = config['environment']
        agg = config['aggregation']
        # Для MinIO writer: output_dir интерпретируем как префикс в бакете (без слеша в начале)
        output_prefix = env['output_dir'].lstrip('/')
        # Создавать папки в MinIO не нужно – write_raster сам создаст объект по ключу

        # 1. Мастер-сетка (эталонный растр) – читаем из MinIO
        print("🏗 Подготовка эталонной сетки...")
        master = self.r_reader.read_raster(env['master_grid'])
        target_crs = env.get('target_crs', 'EPSG:32640')
        if master.meta['crs'].is_geographic:
            master = reproject_raster(master, target_crs=target_crs)
        
        processed_factors = []

        # 2. Обработка критериев
        for crit_config in config['criteria']:
            crit_id = crit_config['id']
            print(f"\n🛠 Обработка критерия: {crit_id} ({crit_config['type']})")
            
            raw_raster = self._calculate_raw_factor(crit_config, master)
            aligned = align_raster(raw_raster, master)
            
            criterion_logic = Criterion.from_dict(crit_config)
            scored = criterion_logic.evaluate(aligned)
            scored = RasterData(values=scored.values, meta=scored.meta, name=crit_id)
            processed_factors.append(scored)

            # Сохраняем промежуточный результат в MinIO
            if env.get('save_intermediate', True):
                # Ключ в MinIO: results/criteria/slope_factor_scored.tif (пример)
                intermediate_key = f"{output_prefix}/{crit_id}_scored.tif"
                self.writer.write_raster(scored, intermediate_key)
                print(f"   → Промежуточный слой сохранён в MinIO: {intermediate_key}")

        # 3. Финальная агрегация
        print(f"\n⚖️ Агрегация методом: {agg['method']}")
        weights = agg['weights_config']
        if agg['method'] == "weighted_sum":
            final_raster = sum_weights(processed_factors, weights)
        elif agg['method'] == "geometric_mean":
            final_raster = geometric_mean_weights(processed_factors, weights)
        else:
            raise ValueError(f"Неизвестный метод агрегации: {agg['method']}")

        # Сохраняем финальный результат в MinIO
        final_key = f"{output_prefix}/FINAL_SUITABILITY.tif"
        self.writer.write_raster(final_raster, final_key)
        print(f"\n✅ Проект завершен успешно! Результат в MinIO: {final_key}")

    def _calculate_raw_factor(self, config, master) -> RasterData:
        c_type = config['type']
        source = config['source']

        if c_type == "slope":
            # source – ключ в MinIO (например, "sources/dem.tif")
            raster = self.r_reader.read_raster(source)
            if raster.meta['crs'].is_geographic:
                # Перепроецируем в метрическую систему (по умолчанию UTM 40N)
                raster = reproject_raster(raster, target_crs="EPSG:32640")
            return calculate_slope(raster)

        elif c_type == "proximity":
            # source – строка вида "vector_data.roads_lines" (схема.таблица)
            # PostGISVectorReader умеет читать такой формат
            vector = self.v_reader.read_vector(source)
            return calculate_proximity(vector, master)

        else:
            raise ValueError(f"Тип критерия {c_type} не поддерживается")