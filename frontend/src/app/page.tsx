'use client';

import { useEffect, useState } from 'react';
import { apiService } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import ChatInterface from '@/components/ChatInterface';
import SystemStatus from '@/components/SystemStatus';
import AdminInterface from '@/components/AdminInterface';
import DashboardComponent from '@/components/Dashboard';
import BrandManager from '@/components/admin/BrandManager';
import CampaignManager from '@/components/admin/CampaignManager';
import SourceManager from '@/components/admin/SourceManager';
import DeleteData from '@/components/DeleteData';
import { Activity, MessageSquare, BarChart3, LogOut, User, Settings, Building, TrendingUp, Globe, Trash2 } from 'lucide-react';

function DashboardContent() {
  const [activeTab, setActiveTab] = useState('overview');
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  useEffect(() => {
    const checkSystemStatus = async () => {
      try {
        const result = await apiService.testConnection();
        setSystemStatus(result);
      } catch (error) {
        setSystemStatus({ success: false, error: 'Failed to connect to API' });
      } finally {
        setIsLoading(false);
      }
    };

    checkSystemStatus();
  }, []);

  const tabs = [
    { id: 'overview', label: 'Dashboard', icon: BarChart3 },
    { id: 'chat', label: 'AI Chat', icon: MessageSquare },
    { id: 'brands', label: 'Brands', icon: Building },
    { id: 'campaigns', label: 'Campaigns', icon: TrendingUp },
    { id: 'sources', label: 'Sources', icon: Globe },
    { id: 'status', label: 'System Status', icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <h1 className="text-2xl font-bold text-gray-900">
                  EchoChamber Analyst
                </h1>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className={`flex items-center space-x-2 ${
                systemStatus?.success ? 'text-green-600' : 'text-red-600'
              }`}>
                <Activity className="h-4 w-4" />
                <span className="text-sm font-medium">
                  {isLoading ? 'Checking...' : systemStatus?.success ? 'Online' : 'Offline'}
                </span>
              </div>

              {/* User Info and Logout */}
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => setActiveTab('admin')}
                  className={`flex items-center space-x-1 px-3 py-1 text-sm rounded-md transition-colors ${
                    activeTab === 'admin'
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <Settings className="h-4 w-4" />
                  <span>Admin</span>
                </button>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-1 px-3 py-1 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Logout</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Dashboard Tab */}
        {activeTab === 'overview' && (
          <DashboardComponent />
        )}

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div>
            <ChatInterface />
          </div>
        )}

        {/* Brands Tab */}
        {activeTab === 'brands' && (
          <div>
            <BrandManager />
          </div>
        )}

        {/* Campaigns Tab */}
        {activeTab === 'campaigns' && (
          <div>
            <CampaignManager />
          </div>
        )}

        {/* Sources Tab */}
        {activeTab === 'sources' && (
          <div>
            <SourceManager />
          </div>
        )}

        {/* Delete Data Tab */}
        {activeTab === 'delete-data' && (
          <div>
            <DeleteData />
          </div>
        )}

        {/* Admin Tab */}
        {activeTab === 'admin' && (
          <div>
            <AdminInterface />
          </div>
        )}

        {/* System Status Tab */}
        {activeTab === 'status' && (
          <div>
            <SystemStatus />
          </div>
        )}
      </main>
    </div>
  );
}

export default function Dashboard() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
