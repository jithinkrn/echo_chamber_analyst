'use client';

import { useEffect, useState } from 'react';
import { apiService } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import ChatInterface from '@/components/ChatInterface';
import SystemStatus from '@/components/SystemStatus';
import SearchInterface from '@/components/SearchInterface';
import AdminInterface from '@/components/AdminInterface';
import { Activity, MessageSquare, Search, BarChart3, LogOut, User, Settings } from 'lucide-react';

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
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'chat', label: 'AI Chat', icon: MessageSquare },
    { id: 'search', label: 'Search', icon: Search },
    { id: 'admin', label: 'Admin', icon: Settings },
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
                <div className="flex items-center space-x-2 text-gray-600">
                  <User className="h-4 w-4" />
                  <span className="text-sm font-medium">{user?.username}</span>
                </div>
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
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Quick Stats Cards */}
              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <Activity className="h-6 w-6 text-gray-400" />
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">
                          System Status
                        </dt>
                        <dd className="text-lg font-medium text-gray-900">
                          {systemStatus?.success ? 'Operational' : 'Issues Detected'}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <MessageSquare className="h-6 w-6 text-gray-400" />
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">
                          AI Agents
                        </dt>
                        <dd className="text-lg font-medium text-gray-900">
                          5 Active
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <Search className="h-6 w-6 text-gray-400" />
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">
                          Content Sources
                        </dt>
                        <dd className="text-lg font-medium text-gray-900">
                          Reddit, Web
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <BarChart3 className="h-6 w-6 text-gray-400" />
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">
                          Analysis Mode
                        </dt>
                        <dd className="text-lg font-medium text-gray-900">
                          Real-time
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Welcome Message */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-6 py-5">
                <h3 className="text-lg leading-6 font-medium text-gray-900">
                  Welcome to EchoChamber Analyst
                </h3>
                <div className="mt-2 max-w-4xl text-sm text-gray-500">
                  <p>
                    Your AI-powered platform for analyzing social media echo chambers and content patterns.
                    Use the tabs above to interact with our multi-agent system:
                  </p>
                  <ul className="mt-4 list-disc list-inside space-y-1">
                    <li><strong>AI Chat:</strong> Ask questions about your analyzed content using our RAG-powered chatbot</li>
                    <li><strong>Search:</strong> Explore processed content and insights across campaigns</li>
                    <li><strong>System Status:</strong> Monitor the health and performance of all AI agents</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div>
            <ChatInterface />
          </div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div>
            <SearchInterface />
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
