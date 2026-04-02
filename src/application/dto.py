from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class CriterionDTO:
    id: str                 # Уникальный ID (например, "c1")
    type: str               # Тип: "slope", "proximity", "reclass"
    source: str             # Путь к файлу: "data/elevation.tif"
    weight: float           # Вес в анализе (0.0 - 1.0)
    params: Dict[str, Any]  # Специфичные настройки (например, units: "degrees")
    normalization: Dict[str, Any] # Правила перевода в шкалу 0-1

@dataclass
class McaProjectDTO:
    project_name: str
    master_grid: str        # Растр-эталон для сетки
    criteria: List[CriterionDTO]
    output_path: str