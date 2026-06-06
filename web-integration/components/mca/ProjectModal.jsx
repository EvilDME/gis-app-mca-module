// src/components/mca/ProjectModal.jsx
import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { useMapStore } from '../../store/useMapStore';
import CriterionModal from './CriterionModal';

export default function ProjectModal({ project, onSave, onClose }) {
  const [name, setName] = useState(project?.name || '');
  const [method, setMethod] = useState(project?.aggregation_method || 'geometric_mean');
  const [criteria, setCriteria] = useState(project?.criteria || []);
  const [studyArea, setStudyArea] = useState(project?.study_area || null);
  const [isHidden, setIsHidden] = useState(false);
  const [backupPolygon, setBackupPolygon] = useState(null);
  const [isCriterionModalOpen, setIsCriterionModalOpen] = useState(false);
  const [editingCriterion, setEditingCriterion] = useState(null);

  const {
    rectangleGeoJson,
    clickMode,
    setClickMode,
    clearRectangle,
    setRectangleGeoJson,
  } = useMapStore();

  // Загрузка проекта: восстанавливаем полигон и studyArea
  useEffect(() => {
    if (project?.study_area) {
      setStudyArea(project.study_area);
      setRectangleGeoJson(project.study_area);
    }
  }, [project, setRectangleGeoJson]);

  // Обновление studyArea при получении нового полигона (после рисования)
  useEffect(() => {
    if (rectangleGeoJson && isHidden) {
      setStudyArea(rectangleGeoJson);
      setIsHidden(false);
    }
  }, [rectangleGeoJson, isHidden]);

  // Отмена рисования – восстановление предыдущего полигона
  useEffect(() => {
    if (clickMode === null && isHidden && backupPolygon !== null) {
      setRectangleGeoJson(backupPolygon);
      setBackupPolygon(null);
      setIsHidden(false);
    }
  }, [clickMode, isHidden, backupPolygon, setRectangleGeoJson]);

  const handleChooseArea = () => {
    setBackupPolygon(rectangleGeoJson);
    setIsHidden(true);
    clearRectangle();
    setClickMode('rectangle');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // Финальный полигон: сначала из свежего rectangleGeoJson, иначе из studyArea
    const finalPolygon = rectangleGeoJson || studyArea;
    if (!project?.id && !finalPolygon) {
      toast.error('Для нового проекта необходимо выбрать область анализа.');
      return;
    }
    const criteriaForApi = criteria.map(({ id, ...rest }) => rest);
    const projectData = {
      name,
      aggregation_method: method,
      criteria: criteriaForApi,
      study_area: finalPolygon,
    };
    onSave(projectData);
  };

  const openAddCriterion = () => {
    setEditingCriterion(null);
    setIsCriterionModalOpen(true);
  };

  const openEditCriterion = (criterion) => {
    setEditingCriterion(criterion);
    setIsCriterionModalOpen(true);
  };

  const saveCriterion = (criterionData) => {
    if (editingCriterion) {
      setCriteria(criteria.map(c => (c.id === editingCriterion.id ? { ...c, ...criterionData } : c)));
    } else {
      setCriteria([...criteria, { id: Date.now(), ...criterionData }]);
    }
    setIsCriterionModalOpen(false);
    setEditingCriterion(null);
  };

  const deleteCriterion = (id) => {
    setCriteria(criteria.filter(c => c.id !== id));
  };

  const isDrawing = clickMode === 'rectangle';
  const pointsCount = useMapStore((state) => state.rectanglePoints.length);
  const buttonText = isDrawing ? `Выбрано точек: ${pointsCount}/4` : 'Выбрать область анализа';
  const hasPolygon = !!(rectangleGeoJson || studyArea);

  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/50 p-4"
      style={{ display: isHidden ? 'none' : 'flex' }}
    >
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-xl font-bold">{project?.id ? 'Редактировать проект' : 'Новый проект'}</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Название</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 p-2"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Метод агрегации</label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 p-2"
            >
              <option value="geometric_mean">Среднее геометрическое</option>
              <option value="weighted_sum">Взвешенная сумма</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Область интереса</label>
            <button
              type="button"
              onClick={handleChooseArea}
              className="mt-1 rounded-lg border border-gray-300 bg-gray-50 px-4 py-2 text-sm hover:bg-gray-100"
            >
              {buttonText}
            </button>
            {hasPolygon && (
              <p className="mt-1 text-xs text-gray-500">Область выбрана, координаты сохранены.</p>
            )}
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="block text-sm font-medium text-gray-700">Критерии</label>
              <button type="button" onClick={openAddCriterion} className="text-sm text-blue-600 hover:underline">
                + Добавить критерий
              </button>
            </div>
            {criteria.length === 0 && <p className="text-sm text-gray-500">Нет критериев. Добавьте хотя бы один.</p>}
            {criteria.map((crit) => (
              <div key={crit.id} className="mb-2 flex items-center justify-between rounded-lg border p-2">
                <div>
                  <span className="font-medium">{crit.analysis_type}</span>
                  <span className="ml-2 text-xs text-gray-500">вес: {crit.weight}</span>
                </div>
                <div className="space-x-2">
                  <button type="button" onClick={() => openEditCriterion(crit)} className="text-xs text-blue-600">
                    Изменить
                  </button>
                  <button type="button" onClick={() => deleteCriterion(crit.id)} className="text-xs text-red-600">
                    Удалить
                  </button>
                </div>
              </div>
            ))}
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

        {isCriterionModalOpen && (
          <CriterionModal
            criterion={editingCriterion}
            onSave={saveCriterion}
            onClose={() => setIsCriterionModalOpen(false)}
          />
        )}
      </div>
    </div>
  );
}   