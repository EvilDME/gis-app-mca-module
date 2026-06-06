import React, { useState, useEffect } from 'react';

const PRESET_POINTS = {
  slope: {
    name: 'Уклон (оптимальный)',
    points: [[0, 1.0], [5, 1.0], [15, 0.2], [30, 0.0]],
    weight: 0.3,
    analysis_type: 'slope',
    data_type: 'dem'
  },
  roads: {
    name: 'Близость к дорогам (оптимальный)',
    points: [[0, 0.2], [300, 1.0], [800, 1.0], [2500, 0.0]],
    weight: 0.5,
    analysis_type: 'proximity',
    data_type: 'roads'
  },
  water: {
    name: 'Близость к воде (оптимальный)',
    points: [[0, 0.0], [200, 0.0], [500, 1.0], [2000, 0.5]],
    weight: 0.2,
    analysis_type: 'proximity',
    data_type: 'water'
  }
};
export default function CriterionModal({ criterion, onSave, onClose }) {
  // Определяем начальный тип на основе переданного criterion (если редактирование)
  const getInitialType = () => {
    if (criterion?.analysis_type === 'slope') return 'slope';
    if (criterion?.analysis_type === 'proximity') {
      if (criterion?.data_type === 'water') return 'water';
      if (criterion?.data_type === 'roads') return 'roads';
    }
    return 'slope'; // по умолчанию
  };

  const [criterionType, setCriterionType] = useState(getInitialType());
  const [weight, setWeight] = useState(criterion?.weight ?? 0.5);
  const [points, setPoints] = useState(criterion?.logic_params?.evaluation?.points || [[0,1],[1,0]]);
  const [selectedPreset, setSelectedPreset] = useState('');

  // При смене типа обновляем точки на рекомендуемый пресет (если пользователь не менял вручную)
  useEffect(() => {
    if (criterionType === 'slope' && !criterion) {
      setPoints(PRESET_POINTS.slope.points);
    } else if (criterionType === 'water' && !criterion) {
      setPoints(PRESET_POINTS.water.points);
    } else if (criterionType === 'roads' && !criterion) {
      setPoints(PRESET_POINTS.roads.points);
    }
  }, [criterionType, criterion]);

    const applyPreset = (presetKey) => {
    const preset = PRESET_POINTS[presetKey];
    if (preset) {
        setSelectedPreset(presetKey);
        setPoints(preset.points);
        setWeight(preset.weight);
        setCriterionType(presetKey); // устанавливает тип (slope/roads/water)
    }
    };

  const handleSubmit = (e) => {
    e.preventDefault();
    let analysis_type = '';
    let data_type = '';

    switch (criterionType) {
      case 'slope':
        analysis_type = 'slope';
        data_type = 'dem';
        break;
      case 'water':
        analysis_type = 'proximity';
        data_type = 'water';
        break;
      case 'roads':
        analysis_type = 'proximity';
        data_type = 'roads';
        break;
      default:
        analysis_type = 'slope';
        data_type = 'dem';
    }

    onSave({
      analysis_type,
      data_type,
      weight,
      logic_params: { evaluation: { points } }
    });
  };

  const addPoint = () => {
    setPoints([...points, [0, 0]]);
  };

  const removePoint = (index) => {
    const newPoints = points.filter((_, i) => i !== index);
    setPoints(newPoints);
  };

  const updatePoint = (index, coord, value) => {
    const newPoints = [...points];
    newPoints[index][coord] = parseFloat(value);
    setPoints(newPoints);
  };

  return (
    <div className="fixed inset-0 z-[2100] flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-xl font-bold">{criterion ? 'Редактировать критерий' : 'Новый критерий'}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
            {/* Пресеты */}
            <div>
                <label className="block text-sm font-medium text-gray-700">Рекомендованные настройки</label>
                <select
                value={selectedPreset}
                onChange={(e) => applyPreset(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 p-2"
                >
                <option value="">-- Выберите пресет --</option>
                <option value="slope">Уклон (оптимальный, вес 0.3)</option>
                <option value="roads">Близость к дорогам (оптимальный, вес 0.5)</option>
                <option value="water">Близость к воде (оптимальный, вес 0.2)</option>
                </select>
            </div>

            {/* Выбор типа критерия */}
            <div>
                <label className="block text-sm font-medium text-gray-700">Тип критерия</label>
                <select
                value={criterionType}
                onChange={(e) => setCriterionType(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 p-2"
                >
                <option value="slope">Уклон</option>
                <option value="water">Близость к воде</option>
                <option value="roads">Близость к дорогам</option>
                </select>
            </div>

            {/* Вес */}
            <div>
                <label className="block text-sm font-medium text-gray-700">Вес (0..1)</label>
                <input type="range" min="0" max="1" step="0.05" value={weight} onChange={(e) => setWeight(parseFloat(e.target.value))} className="mt-1 w-full" />
                <div className="text-center text-sm">{weight}</div>
            </div>

          {/* Точки интерполяции */}
          <div>
            <label className="block text-sm font-medium text-gray-700">Точки интерполяции (x, y)</label>
            <div className="mt-1 space-y-2">
              {points.map((point, idx) => (
                <div key={idx} className="flex gap-2 items-center">
                  <input
                    type="number"
                    value={point[0]}
                    onChange={(e) => updatePoint(idx, 0, e.target.value)}
                    placeholder="x"
                    className="w-24 rounded border p-1 text-sm"
                  />
                  <input
                    type="number"
                    value={point[1]}
                    onChange={(e) => updatePoint(idx, 1, e.target.value)}
                    placeholder="y"
                    className="w-24 rounded border p-1 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => removePoint(idx)}
                    className="text-red-500 text-sm"
                  >
                    Удалить
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={addPoint}
                className="text-sm text-blue-600"
              >
                + Добавить точку
              </button>
            </div>
            <p className="mt-2 text-xs text-gray-500">
              X – значение исходного параметра, Y – оценка (0..1).
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <button type="button" onClick={onClose} className="rounded-lg border border-gray-300 px-4 py-2">
              Отмена
            </button>
            <button type="submit" className="rounded-lg bg-blue-600 px-4 py-2 text-white">
              Сохранить
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}