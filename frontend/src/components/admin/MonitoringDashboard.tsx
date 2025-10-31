import React, { useState, useEffect } from 'react';
import api from '../../lib/api';

interface CeleryTask {
  active: number;
  scheduled: number;
  reserved: number;
  workers: string[];
}

interface WorkflowStats {
  total_insights_24h: number;
  total_content_24h: number;
  active_campaigns: number;
  total_campaigns: number;
}

interface Monitoring {
  total_events: number;
  error_rate: number;
  recent_errors: any[];
  langsmith_enabled: boolean;
}

interface SystemHealth {
  database: string;
  celery: string;
  monitoring: string;
}

interface MonitoringData {
  timestamp: string;
  celery_tasks: CeleryTask;
  workflow_stats: WorkflowStats;
  monitoring: Monitoring;
  system_health: SystemHealth;
}

interface AgentHealth {
  [key: string]: {
    status: string;
    available: boolean;
    last_check: string;
  };
}

export function MonitoringDashboard() {
  const [monitoringData, setMonitoringData] = useState<MonitoringData | null>(null);
  const [agentHealth, setAgentHealth] = useState<{ overall_status: string; agents: AgentHealth } | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds

  const fetchMonitoringData = async () => {
    try {
      const [dashboardData, healthData] = await Promise.all([
        api.get('/monitoring/dashboard/'),
        api.get('/monitoring/agents/health/')
      ]);

      setMonitoringData(dashboardData.data);
      setAgentHealth(healthData.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch monitoring data:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMonitoringData();

    const interval = setInterval(fetchMonitoringData, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  const triggerTask = async (taskType: string, payload: any = {}) => {
    try {
      const response = await api.post(`/tasks/${taskType}/`, payload);
      alert(`Task triggered successfully! Task ID: ${response.data.task_id}`);
      fetchMonitoringData();
    } catch (error) {
      console.error(`Failed to trigger ${taskType} task:`, error);
      alert(`Failed to trigger task: ${error}`);
    }
  };

  const restartAgent = async (agentName: string) => {
    try {
      await api.post(`/monitoring/agents/${agentName}/restart/`);
      alert(`Agent ${agentName} restarted successfully`);
      fetchMonitoringData();
    } catch (error) {
      console.error(`Failed to restart agent:`, error);
      alert(`Failed to restart agent: ${error}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-600">Loading monitoring data...</div>
      </div>
    );
  }

  if (!monitoringData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-red-600">Failed to load monitoring data</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">System Monitoring Dashboard</h2>
        <div className="flex items-center space-x-4">
          <select
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(Number(e.target.value))}
            className="px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value={10000}>Refresh: 10s</option>
            <option value={30000}>Refresh: 30s</option>
            <option value={60000}>Refresh: 1min</option>
          </select>
          <button
            onClick={fetchMonitoringData}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Refresh Now
          </button>
        </div>
      </div>

      {/* System Health Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Database</h3>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              monitoringData.system_health.database === 'connected'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}>
              {monitoringData.system_health.database}
            </span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Celery Workers</h3>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              monitoringData.system_health.celery === 'healthy'
                ? 'bg-green-100 text-green-800'
                : 'bg-yellow-100 text-yellow-800'
            }`}>
              {monitoringData.system_health.celery}
            </span>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Monitoring</h3>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              monitoringData.system_health.monitoring === 'active'
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
            }`}>
              {monitoringData.system_health.monitoring}
            </span>
          </div>
        </div>
      </div>

      {/* Celery Tasks Stats */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Celery Task Queue</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">{monitoringData.celery_tasks.active}</div>
            <div className="text-sm text-gray-600">Active Tasks</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-600">{monitoringData.celery_tasks.scheduled}</div>
            <div className="text-sm text-gray-600">Scheduled Tasks</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600">{monitoringData.celery_tasks.reserved}</div>
            <div className="text-sm text-gray-600">Reserved Tasks</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">{monitoringData.celery_tasks.workers.length}</div>
            <div className="text-sm text-gray-600">Active Workers</div>
          </div>
        </div>
        {monitoringData.celery_tasks.workers.length > 0 && (
          <div className="mt-4 text-sm text-gray-600">
            <strong>Workers:</strong> {monitoringData.celery_tasks.workers.join(', ')}
          </div>
        )}
      </div>

      {/* Workflow Statistics */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Workflow Statistics (24h)</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-indigo-600">{monitoringData.workflow_stats.total_insights_24h}</div>
            <div className="text-sm text-gray-600">Insights Generated</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-cyan-600">{monitoringData.workflow_stats.total_content_24h}</div>
            <div className="text-sm text-gray-600">Content Processed</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-emerald-600">{monitoringData.workflow_stats.active_campaigns}</div>
            <div className="text-sm text-gray-600">Active Campaigns</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-slate-600">{monitoringData.workflow_stats.total_campaigns}</div>
            <div className="text-sm text-gray-600">Total Campaigns</div>
          </div>
        </div>
      </div>

      {/* Agent Health Status */}
      {agentHealth && (
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Agent Health Status</h3>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              agentHealth.overall_status === 'healthy'
                ? 'bg-green-100 text-green-800'
                : 'bg-yellow-100 text-yellow-800'
            }`}>
              {agentHealth.overall_status.toUpperCase()}
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(agentHealth.agents).map(([agentName, health]) => (
              <div key={agentName} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900">{agentName}</h4>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    health.status === 'healthy'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {health.status}
                  </span>
                </div>
                <div className="text-xs text-gray-500 mb-2">
                  Available: {health.available ? 'Yes' : 'No'}
                </div>
                <button
                  onClick={() => restartAgent(agentName)}
                  className="w-full px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                >
                  Restart Agent
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Monitoring Events */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Monitoring Events</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">{monitoringData.monitoring.total_events}</div>
            <div className="text-sm text-gray-600">Total Events</div>
          </div>
          <div className="text-center">
            <div className={`text-3xl font-bold ${
              monitoringData.monitoring.error_rate > 10 ? 'text-red-600' : 'text-green-600'
            }`}>
              {monitoringData.monitoring.error_rate.toFixed(2)}%
            </div>
            <div className="text-sm text-gray-600">Error Rate</div>
          </div>
          <div className="text-center">
            <div className={`text-3xl font-bold ${
              monitoringData.monitoring.langsmith_enabled ? 'text-green-600' : 'text-gray-400'
            }`}>
              {monitoringData.monitoring.langsmith_enabled ? 'ON' : 'OFF'}
            </div>
            <div className="text-sm text-gray-600">LangSmith</div>
          </div>
        </div>
        {monitoringData.monitoring.recent_errors.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Recent Errors:</h4>
            <div className="bg-red-50 rounded-lg p-3 max-h-48 overflow-y-auto">
              {monitoringData.monitoring.recent_errors.map((error, idx) => (
                <div key={idx} className="text-xs text-red-800 mb-1">
                  {error.timestamp}: {error.event_type} - {error.error || 'Unknown error'}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Task Controls */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Manual Task Controls</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <button
            onClick={() => triggerTask('scout')}
            className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Run Scout Task
          </button>
          <button
            onClick={() => triggerTask('insights')}
            className="px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
          >
            Generate Insights
          </button>
          <button
            onClick={() => triggerTask('cleanup', { days_to_keep: 90 })}
            className="px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition"
          >
            Run Cleanup
          </button>
          <button
            onClick={() => {
              const campaignId = prompt('Enter Campaign ID:');
              if (campaignId) {
                triggerTask('workflow', { campaign_id: parseInt(campaignId) });
              }
            }}
            className="px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
          >
            Run Workflow
          </button>
        </div>
      </div>

      {/* Timestamp */}
      <div className="text-center text-sm text-gray-500">
        Last updated: {new Date(monitoringData.timestamp).toLocaleString()}
      </div>
    </div>
  );
}
