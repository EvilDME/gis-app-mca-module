// src/store/useModalStore.js
import { create } from 'zustand';

const useModalStore = create((set, get) => ({
  projectModalOpen: false,
  editingProject: null,
  openProjectModal: async (project = null) => {
    if (project && project.id) {
      // Загружаем полные данные проекта
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/mca/projects/${project.id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const fullProject = await res.json();
          set({ projectModalOpen: true, editingProject: fullProject });
        } else {
          // fallback – используем то, что есть
          set({ projectModalOpen: true, editingProject: project });
        }
      } catch (err) {
        console.error('Failed to load project details', err);
        set({ projectModalOpen: true, editingProject: project });
      }
    } else {
      set({ projectModalOpen: true, editingProject: null });
    }
  },
  closeProjectModal: () => set({ projectModalOpen: false, editingProject: null }),

  criterionModalOpen: false,
  editingCriterion: null,
  currentProjectId: null,
  openCriterionModal: (criterion = null, projectId = null) =>
    set({ criterionModalOpen: true, editingCriterion: criterion, currentProjectId: projectId }),
  closeCriterionModal: () => set({ criterionModalOpen: false, editingCriterion: null, currentProjectId: null }),
}));

export default useModalStore;