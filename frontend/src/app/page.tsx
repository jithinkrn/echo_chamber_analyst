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
import DeleteData from '@/components/DeleteData';
import { Activity, MessageSquare, BarChart3, LogOut, User, Settings, Building, TrendingUp, Trash2 } from 'lucide-react';

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
    { id: 'status', label: 'System Status', icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Enhanced Header */}
      <header className="bg-gradient-to-r from-slate-800 via-slate-700 to-slate-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-24">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0 bg-white/10 backdrop-blur-sm rounded-lg p-2">
                <Activity className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white tracking-tight">
                  EchoChamber Analyst
                </h1>
                <p className="text-xs text-slate-300">AI-Powered Brand Intelligence</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* System Status Badge */}
              <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full backdrop-blur-sm ${
                systemStatus?.success 
                  ? 'bg-green-500/20 border border-green-400/30' 
                  : 'bg-red-500/20 border border-red-400/30'
              }`}>
                <div className={`h-2 w-2 rounded-full ${
                  systemStatus?.success ? 'bg-green-400 animate-pulse' : 'bg-red-400'
                }`} />
                <span className="text-sm font-medium text-white">
                  {isLoading ? 'Checking...' : systemStatus?.success ? 'Online' : 'Offline'}
                </span>
              </div>

              {/* User Controls */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setActiveTab('admin')}
                  className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                    activeTab === 'admin'
                      ? 'bg-white text-slate-700 shadow-md'
                      : 'bg-white/10 text-white hover:bg-white/20 backdrop-blur-sm'
                  }`}
                >
                  <Settings className="h-4 w-4" />
                  <span>Admin</span>
                </button>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-2 px-4 py-2 text-sm font-medium bg-white/10 text-white hover:bg-red-500/20 hover:border-red-400/30 border border-white/20 rounded-lg transition-all backdrop-blur-sm"
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

      {/* Footer */}
      <footer className="bg-gradient-to-r from-slate-800 via-slate-700 to-slate-800 border-t border-slate-600/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            {/* Left side - Brand info */}
            <div className="flex items-center space-x-3">
              <div className="bg-white/10 backdrop-blur-sm rounded-lg p-2">
                <Activity className="h-5 w-5 text-white" />
              </div>
              <div>
                <p className="text-white font-semibold">EchoChamber Analyst</p>
                <p className="text-xs text-slate-300">AI-Powered Brand Intelligence Platform</p>
              </div>
            </div>

            {/* Center - Copyright */}
            <div className="text-center">
              <p className="text-sm text-white/90">
                © {new Date().getFullYear()} EchoChamber Analyst. All rights reserved.
              </p>
              <p className="text-xs text-slate-300 mt-1">
                Empowering brands with actionable insights
              </p>
            </div>

            {/* Right side - Version/Status */}
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-xs text-slate-300">Version 2.0.0</p>
                <div className="flex items-center justify-end space-x-1 mt-1">
                  <div className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-xs text-white/90">System Operational</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </footer>
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
