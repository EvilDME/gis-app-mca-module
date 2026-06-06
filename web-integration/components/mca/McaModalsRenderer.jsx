import React from 'react';
import { useMapStore } from '../../store/useMapStore';
import useModalStore from '../../store/useModalStore';
import ProjectModal from './ProjectModal';
import CriterionModal from './CriterionModal';
import toast from 'react-hot-toast';

export default function McaModalsRenderer() {
  const { token } = useMapStore();
  const {
    projectModalOpen,
    criterionModalOpen,
    editingProject,
    editingCriterion,
    currentProjectId,
    closeProjectModal,
    closeCriterionModal,
  } = useModalStore();

  const handleSaveProject = async (projectData) => {
    if (!token) {
      toast.error('Необходима авторизация');
      return;
    }

    try {
      const isNew = !editingProject?.id;
      const url = isNew
        ? '/api/mca/projects/with-criteria'
        : `/api/mca/projects/${editingProject.id}/with-criteria`;
      const method = isNew ? 'POST' : 'PUT';

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(projectData),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Ошибка сохранения проекта');
      }

      toast.success(isNew ? 'Проект создан' : 'Проект обновлён');
      window.dispatchEvent(new Event('projects-updated'));
      closeProjectModal();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleSaveCriterion = async (criterionData) => {
    if (!token || !currentProjectId) return;
    try {
      const isNew = !editingCriterion?.id;
      let url, method;
      if (isNew) {
        url = `/api/mca/projects/${currentProjectId}/criteria`;
        method = 'POST';
      } else {
        url = `/api/mca/criteria/${editingCriterion.id}`;
        method = 'PUT';
      }
      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(criterionData),
      });
      if (!res.ok) throw new Error('Ошибка сохранения критерия');
      toast.success(isNew ? 'Критерий добавлен' : 'Критерий обновлён');
      window.dispatchEvent(new Event('projects-updated'));
      closeCriterionModal();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      {projectModalOpen && (
        <ProjectModal
          project={editingProject}
          onSave={handleSaveProject}
          onClose={closeProjectModal}
        />
      )}
      {criterionModalOpen && (
        <CriterionModal
          criterion={editingCriterion}
          projectId={currentProjectId}
          onSave={handleSaveCriterion}
          onClose={closeCriterionModal}
        />
      )}
    </>
  );
}