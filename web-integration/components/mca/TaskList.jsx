import React, { useState, useEffect } from 'react';
import { useMapStore } from '../../store/useMapStore';
import useRasterDisplayStore from '../../store/useRasterDisplayStore';
import toast from 'react-hot-toast';

export default function TaskList() {
  const { token } = useMapStore();
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [expandedTaskId, setExpandedTaskId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const { displayResultId, setDisplayResultId, setDisplayRasterUrl, setDisplayRasterBounds, clearDisplayRaster } = useRasterDisplayStore();

  // Load project list for dropdown
  useEffect(() => {
    if (!token) return;
    fetch('/api/mca/projects', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setProjects(data))
      .catch((err) => console.error(err));
  }, [token]);

  // Load tasks when a project is selected
  useEffect(() => {
    if (!selectedProjectId || !token) return;
    fetch(`/api/mca/projects/${selectedProjectId}/tasks`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setTasks(data))
      .catch((err) => console.error(err));
  }, [selectedProjectId, token]);

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
      // Refresh tasks
      const tasksRes = await fetch(`/api/mca/projects/${selectedProjectId}/tasks`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const newTasks = await tasksRes.json();
      setTasks(newTasks);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchTaskDetails = async (taskId) => {
    const res = await fetch(`/api/mca/task/${taskId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Ошибка загрузки деталей');
    return res.json();
  };

  const showResult = async (resultId) => {
    console.log('[showResult] Fetching result', resultId);
    try {
      const res = await fetch(`/api/mca/results/${resultId}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Ошибка получения ссылки');
      const data = await res.json();
      console.log('[showResult] Received data:', data);
      const previewUrl = data.preview_url || data.download_url?.replace('.tif', '.png');
      if (!previewUrl) throw new Error('No preview URL available');
      setDisplayRasterUrl(previewUrl);
      setDisplayRasterBounds(data.bbox);
      setDisplayResultId(resultId);
    } catch (err) {
      console.error('showResult error:', err);
      toast.error('Не удалось загрузить растр для отображения');
    }
  };

  const downloadResult = async (resultId) => {
    try {
      const res = await fetch(`/api/mca/results/${resultId}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      window.open(data.download_url, '_blank');
    } catch (err) {
      toast.error('Не удалось получить ссылку на скачивание');
    }
  };

    const hideResult = () => {
        clearDisplayRaster();
    };
  return (
    <div>
      <div className="mb-3">
        <label className="block text-sm font-medium text-gray-700">Выберите проект</label>
        <select
          value={selectedProjectId || ''}
          onChange={(e) => setSelectedProjectId(e.target.value)}
          className="mt-1 w-full rounded-lg border border-gray-300 p-2"
        >
          <option value="">-- Выберите проект --</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      <button
        className="mb-3 w-full rounded-xl bg-green-600 py-2 text-sm font-semibold text-white disabled:bg-gray-400"
        onClick={runAnalysis}
        disabled={!selectedProjectId || isLoading}
      >
        {isLoading ? 'Запуск...' : 'Запустить анализ'}
      </button>

      <div className="space-y-2">
        {tasks.length === 0 && <p className="text-sm text-gray-500">Нет задач для этого проекта</p>}
        {tasks.map((task) => (
          <div key={task.id} className="rounded-xl border border-gray-200 bg-white p-3">
            <div
              className="flex cursor-pointer items-center justify-between"
              onClick={async () => {
                if (expandedTaskId === task.id) {
                  setExpandedTaskId(null);
                } else {
                  try {
                    const fullTask = await fetchTaskDetails(task.id);
                    task.results = fullTask.results; // inject results into task object
                    setExpandedTaskId(task.id);
                  } catch (err) {
                    toast.error(err.message);
                  }
                }
              }}
            >
              <div>
                <span className="font-medium">Задача от {new Date(task.created_at).toLocaleDateString()}</span>
                <span className="ml-2 text-xs text-gray-500">Статус: {task.status}</span>
              </div>
              <span>{expandedTaskId === task.id ? '▲' : '▼'}</span>
            </div>
            {expandedTaskId === task.id && task.results && (
              <div className="mt-3 space-y-2 border-t pt-2">
                {task.results.map((res) => (
                  <div key={res.id} className="flex items-center justify-between text-sm">
                    <span>{res.name}</span>
                    <div className="space-x-2">
                      <button
                        onClick={() => downloadResult(res.id)}
                        className="rounded bg-blue-100 px-2 py-1 text-blue-700"
                      >
                        Скачать
                      </button>
                        <button
                        onClick={() => {
                            if (displayResultId === res.id) {
                            hideResult();
                            } else {
                            showResult(res.id);
                            }
                        }}
                        className={`rounded px-2 py-1 ${
                            displayResultId === res.id ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                        }`}
                        >
                        {displayResultId === res.id ? 'Скрыть' : 'Отобразить'}
                        </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}