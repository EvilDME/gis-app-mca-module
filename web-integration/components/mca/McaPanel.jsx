import React, { useState } from 'react';
import ProjectList from './ProjectList';
import TaskList from './TaskList';

export default function McaPanel() {
  const [activeTab, setActiveTab] = useState('projects');

  return (
    <div className="space-y-3">
      <div className="flex border-b border-gray-200">
        <button
          className={`px-4 py-2 text-sm font-semibold ${
            activeTab === 'projects'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
          onClick={() => setActiveTab('projects')}
        >
          Проекты
        </button>
        <button
          className={`px-4 py-2 text-sm font-semibold ${
            activeTab === 'run'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
          onClick={() => setActiveTab('run')}
        >
          Запуск и результаты
        </button>
      </div>

      {activeTab === 'projects' && <ProjectList />}
      {activeTab === 'run' && <TaskList />}
    </div>
  );
}