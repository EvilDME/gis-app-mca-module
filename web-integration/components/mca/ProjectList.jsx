// src/components/mca/ProjectList.jsx
import React, { useState, useEffect } from 'react';
import { useMapStore } from '../../store/useMapStore';
import useModalStore from '../../store/useModalStore';
import toast from 'react-hot-toast';

export default function ProjectList() {
  const { token } = useMapStore();
  const openProjectModal = useModalStore((state) => state.openProjectModal);
  const [projects, setProjects] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchProjects = async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const res = await fetch('/api/mca/projects', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Ошибка загрузки проектов');
      const data = await res.json();
      setProjects(data);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setIsLoading(false);
    }
  };

    useEffect(() => {
    fetchProjects();
    const handleUpdate = () => fetchProjects();
    window.addEventListener('projects-updated', handleUpdate);
    return () => window.removeEventListener('projects-updated', handleUpdate);
    }, [token]);

  const openCreateModal = () => openProjectModal(null);
  const openEditModal = (project) => openProjectModal(project);

  return (
    <div>
      <button
        onClick={openCreateModal}
        className="mb-3 w-full rounded-xl bg-blue-600 py-2 text-sm font-semibold text-white"
      >
        + Новый проект
      </button>

      {isLoading && <p className="text-center text-sm text-gray-500">Загрузка...</p>}

      <div className="max-h-80 overflow-y-auto space-y-2 pr-1">
        {projects.length === 0 && !isLoading && (
          <p className="text-sm text-gray-500">Нет проектов. Создайте первый.</p>
        )}
        {projects.map((proj) => (
            <div key={proj.id} className="rounded-xl border border-gray-200 bg-white p-3 shadow-sm">
            <div className="flex items-start justify-between">
                <h4 className="font-semibold">{proj.name}</h4>
                <button
                onClick={() => openEditModal(proj)}
                className="rounded bg-gray-100 px-2 py-1 text-xs text-gray-700"
                >
                Редактировать
                </button>
            </div>
            </div>
        ))}
      </div>
    </div>
  );
}