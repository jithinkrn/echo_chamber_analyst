'use client';

import { useState } from 'react';
import {
  Users,
  Settings,
  Trash2
} from 'lucide-react';
import UserManager from './admin/UserManager';
import SettingsManager from './admin/SettingsManager';
import DeleteData from './DeleteData';

export default function AdminInterface() {
  const [activeSection, setActiveSection] = useState('settings');

  const adminSections = [
    { id: 'settings', label: 'Settings', icon: Settings, description: 'Campaign schedule settings' },
    { id: 'delete-data', label: 'Delete Data', icon: Trash2, description: 'Remove brand analytics or campaign data' },
    { id: 'users', label: 'Users', icon: Users, description: 'Manage user accounts' },
  ];

  const renderActiveSection = () => {
    switch (activeSection) {
      case 'settings':
        return <SettingsManager />;
      case 'delete-data':
        return <DeleteData />;
      case 'users':
        return <UserManager />;
      default:
        return <SettingsManager />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Admin Header */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            System Administration
          </h2>
          <p className="mt-1 text-sm text-gray-600">
            Manage campaigns, sources, content, and system settings
          </p>
        </div>

        {/* Admin Navigation */}
        <div className="px-6 py-4">
          <nav className="flex space-x-4">
            {adminSections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeSection === section.id
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{section.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Active Section Content */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-gray-900">
                {adminSections.find(s => s.id === activeSection)?.label}
              </h3>
              <p className="mt-1 text-sm text-gray-600">
                {adminSections.find(s => s.id === activeSection)?.description}
              </p>
            </div>
          </div>
        </div>

        <div className="p-6">
          {renderActiveSection()}
        </div>
      </div>
    </div>
  );
}