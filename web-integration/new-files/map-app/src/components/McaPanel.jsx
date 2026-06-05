import React, { useState, useEffect } from 'react';
import { useMapStore } from '../store/useMapStore';
import toast from 'react-hot-toast';

export default function McaPanel() {
  const { token, user } = useMapStore();
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [taskStatus, setTaskStatus] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // Загрузка проектов
  const fetchProjects = async () => {
    if (!token) return;
    try {
      const res = await fetch('/api/mca/projects', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to fetch projects');
      const data = await res.json();
      setProjects(data);
    } catch (err) {
      toast.error(err.message);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [token]);

  // Создание тестового проекта
    const createTestProject = async () => {
    if (!token) {
        toast.error('Необходима авторизация');
        return;
    }
    setIsLoading(true);
    const studyArea = {
        type: 'Polygon',
        coordinates: [
        [
            [55.98529815673829, 54.651590680027155],
            [55.98117828369141, 54.68574039669345],
            [56.004867553710945, 54.688121863624445],
            [56.003837585449226, 54.67244130476413],
            [55.98529815673829, 54.651590680027155],
        ],
        ],
    };
    try {
        // 1. Создаём проект
        const projectRes = await fetch('/api/mca/projects', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            name: 'Тестовый проект1',
            study_area: studyArea,
            aggregation_method: 'geometric_mean',
        }),
        });
        if (!projectRes.ok) {
        const errData = await projectRes.json();
        throw new Error(errData.detail || 'Ошибка создания проекта');
        }
        const newProject = await projectRes.json();
        toast.success('Проект создан');

        // 2. Добавляем критерий типа slope
        const criterionRes = await fetch(`/api/mca/projects/${newProject.id}/criteria`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
            analysis_type: 'slope',
            weight: 1.0,
            logic_params: {
            evaluation: { points: [[0, 1], [15, 0.8], [30, 0.2], [45, 0]] },
            },
        }),
        });
        if (!criterionRes.ok) {
        const errData = await criterionRes.json();
        throw new Error(errData.detail || 'Ошибка добавления критерия');
        }
        toast.success('Критерий добавлен');

        // 3. Обновляем список проектов и выбираем созданный
        await fetchProjects();
        setSelectedProjectId(newProject.id);
    } catch (err) {
        toast.error(err.message);
    } finally {
        setIsLoading(false);
    }
    };

  // Запуск анализа по выбранному проекту
  const runAnalysis = async () => {
    if (!selectedProjectId) {
      toast.error('Выберите проект');
      return;
    }
    setIsLoading(true);
    try {
      const res = await fetch(`/api/mca/projects/${selectedProjectId}/run`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Ошибка запуска');
      const { task_id } = await res.json();
      toast.success(`Задача запущена (ID: ${task_id})`);
      startPolling(task_id);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Опрос статуса задачи
  const startPolling = (taskId) => {
    if (pollingInterval) clearInterval(pollingInterval);
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/mca/task/${taskId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        setTaskStatus(data);
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          clearInterval(interval);
          setPollingInterval(null);
          if (data.status === 'COMPLETED') {
            toast.success('Анализ завершён');
          } else {
            toast.error(`Ошибка: ${data.error_message}`);
          }
        }
      } catch (err) {
        console.error(err);
        clearInterval(interval);
        setPollingInterval(null);
      }
    }, 2000);
    setPollingInterval(interval);
  };

  // Скачивание результата
  const downloadResult = async (resultId) => {
    try {
      const res = await fetch(`/api/mca/results/${resultId}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      window.location.assign(data.download_url);
    } catch (err) {
      toast.error('Не удалось получить ссылку на скачивание');
    }
  };

  // Очистка интервала при размонтировании
  useEffect(() => {
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, [pollingInterval]);

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-gray-200 bg-white p-4">
        <h3 className="mb-3 text-sm font-bold text-slate-800">Анализ пригодности территории</h3>
        {!token ? (
          <p className="text-sm text-red-600">Для работы с модулем необходимо авторизоваться</p>
        ) : (
          <>
            <button
              onClick={createTestProject}
              disabled={isLoading}
              className="mb-3 w-full rounded-xl bg-blue-600 py-2 text-sm font-semibold text-white hover:bg-blue-700"
            >
              Создать тестовый проект
            </button>

            {projects.length > 0 && (
              <div className="mb-3">
                <select
                  value={selectedProjectId || ''}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full rounded-xl border border-gray-300 p-2 text-sm"
                >
                  <option value="">Выберите проект</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              onClick={runAnalysis}
              disabled={!selectedProjectId || isLoading}
              className="w-full rounded-xl bg-green-600 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:bg-gray-300"
            >
              Запустить анализ
            </button>

            {taskStatus && taskStatus.status === 'COMPLETED' && taskStatus.results?.length > 0 && (
              <div className="mt-4 rounded-xl border border-gray-200 p-3">
                <h4 className="mb-2 text-sm font-bold">Результаты:</h4>
                <ul className="space-y-1">
                  {taskStatus.results.map((res) => (
                    <li key={res.id} className="flex items-center justify-between text-xs">
                      <span>{res.name}</span>
                      <button
                        onClick={() => downloadResult(res.id)}
                        className="rounded bg-blue-100 px-2 py-1 text-blue-700 hover:bg-blue-200"
                      >
                        Скачать
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {taskStatus && taskStatus.status === 'PROCESSING' && (
              <p className="mt-2 text-center text-sm text-yellow-600">Выполняется анализ...</p>
            )}
            {taskStatus && taskStatus.status === 'FAILED' && (
              <p className="mt-2 text-center text-sm text-red-600">Ошибка: {taskStatus.error_message}</p>
            )}
          </>
        )}
      </div>
    </div>
  );
}