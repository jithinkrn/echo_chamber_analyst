'use client';

import { useState, useEffect } from 'react';
import { apiService } from '@/lib/api';
import { CheckCircle, XCircle, AlertCircle, RefreshCw, Activity, Cpu, Database, Zap } from 'lucide-react';

interface SystemInfo {
  message: string;
  version: string;
  endpoints: Record<string, string>;
}

interface AgentInfo {
  agent_name: string;
  status: 'healthy' | 'offline' | 'unknown';
  capabilities: string[];
  success_rate: number;
  avg_response_time: number;
}

interface LegacyAgentInfo {
  name: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  capabilities: number;
  description: string;
}

export default function SystemStatus() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [lastCheck, setLastCheck] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agentsData, setAgentsData] = useState<AgentInfo[]>([]);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);

  // Fallback agent data for when API is not available
  const fallbackAgents: LegacyAgentInfo[] = [
    {
      name: 'Orchestrator Agent',
      status: 'healthy',
      capabilities: 9,
      description: 'StateGraph orchestration and workflow management',
    },
    {
      name: 'Scout Agent',
      status: 'healthy',
      capabilities: 5,
      description: 'Content discovery and web scraping',
    },
    {
      name: 'Data Cleaner Agent',
      status: 'healthy',
      capabilities: 7,
      description: 'Content cleaning and validation',
    },
    {
      name: 'Analyst Agent',
      status: 'healthy',
      capabilities: 10,
      description: 'LLM-powered content analysis',
    },
    {
      name: 'Chatbot Agent',
      status: 'healthy',
      capabilities: 7,
      description: 'RAG-powered conversational interface',
    },
    {
      name: 'Monitoring Agent',
      status: 'healthy',
      capabilities: 8,
      description: 'LangSmith integration and observability',
    },
  ];

  const getAgentDisplayName = (agentName: string): string => {
    const nameMap: Record<string, string> = {
      'scout_node': 'Scout Agent',
      'cleaner_node': 'Data Cleaner Agent',
      'analyst_node': 'Analyst Agent',
      'chatbot_node': 'Chatbot Agent',
      'workflow_orchestrator': 'Orchestrator Agent',
      'monitoring_agent': 'Monitoring Agent'
    };
    return nameMap[agentName] || agentName;
  };

  const getAgentDescription = (agentName: string): string => {
    const descMap: Record<string, string> = {
      'scout_node': 'Content discovery and web scraping',
      'cleaner_node': 'Content cleaning and validation',
      'analyst_node': 'LLM-powered content analysis',
      'chatbot_node': 'RAG-powered conversational interface',
      'workflow_orchestrator': 'StateGraph orchestration and workflow management',
      'monitoring_agent': 'LangSmith integration and observability'
    };
    return descMap[agentName] || 'AI agent for specialized tasks';
  };

  const fetchAgentsStatus = async () => {
    setIsLoadingAgents(true);
    try {
      // Try to fetch real agents data from API
      const response = await fetch('http://localhost:8003/api/v1/admin/agents/status/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setAgentsData(data);
      } else {
        // Fallback to hardcoded data
        console.warn('Could not fetch agents status, using fallback data');
      }
    } catch (error) {
      console.warn('Error fetching agents status:', error);
    } finally {
      setIsLoadingAgents(false);
    }
  };

  const checkSystemStatus = async () => {
    setConnectionStatus('checking');
    setError(null);

    try {
      const result = await apiService.testConnection();
      if (result.success) {
        setSystemInfo(result.data);
        setConnectionStatus('connected');
      } else {
        setConnectionStatus('disconnected');
        setError(result.error || 'Unknown error');
      }
    } catch (err) {
      setConnectionStatus('disconnected');
      setError(err instanceof Error ? err.message : 'Connection failed');
    } finally {
      setLastCheck(new Date());
    }
  };

  useEffect(() => {
    checkSystemStatus();
    fetchAgentsStatus();
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      checkSystemStatus();
      fetchAgentsStatus();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // Get display agents data - prefer API data, fallback to mock data
  const displayAgents = agentsData.length > 0 ? 
    agentsData.map(agent => ({
      name: getAgentDisplayName(agent.agent_name),
      status: agent.status as 'healthy' | 'unhealthy' | 'unknown',
      capabilities: agent.capabilities.length,
      description: getAgentDescription(agent.agent_name)
    })) : 
    fallbackAgents;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'connected':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'unhealthy':
      case 'disconnected':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'checking':
        return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'connected':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'unhealthy':
      case 'disconnected':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'checking':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* System Overview */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium text-gray-900">System Overview</h3>
            <button
              onClick={checkSystemStatus}
              disabled={connectionStatus === 'checking'}
              className="inline-flex items-center px-3 py-1 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${connectionStatus === 'checking' ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        <div className="px-6 py-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* API Connection */}
            <div className={`p-4 rounded-lg border ${getStatusColor(connectionStatus)}`}>
              <div className="flex items-center">
                {getStatusIcon(connectionStatus)}
                <div className="ml-3">
                  <p className="text-sm font-medium">API Connection</p>
                  <p className="text-xs capitalize">{connectionStatus}</p>
                </div>
              </div>
            </div>

            {/* Total Agents */}
            <div className="p-4 rounded-lg border bg-blue-50 text-blue-600 border-blue-200">
              <div className="flex items-center">
                <Cpu className="h-5 w-5" />
                <div className="ml-3">
                  <p className="text-sm font-medium">AI Agents</p>
                  <p className="text-xs">{displayAgents.length} Active</p>
                </div>
              </div>
            </div>

            {/* Total Capabilities */}
            <div className="p-4 rounded-lg border bg-purple-50 text-purple-600 border-purple-200">
              <div className="flex items-center">
                <Zap className="h-5 w-5" />
                <div className="ml-3">
                  <p className="text-sm font-medium">Capabilities</p>
                  <p className="text-xs">{displayAgents.reduce((sum: number, agent: any) => sum + agent.capabilities, 0)} Total</p>
                </div>
              </div>
            </div>

            {/* System Version */}
            <div className="p-4 rounded-lg border bg-gray-50 text-gray-600 border-gray-200">
              <div className="flex items-center">
                <Database className="h-5 w-5" />
                <div className="ml-3">
                  <p className="text-sm font-medium">Version</p>
                  <p className="text-xs">{systemInfo?.version || '1.0.0'}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Last Check */}
          {lastCheck && (
            <div className="mt-4 text-xs text-gray-500">
              Last checked: {lastCheck.toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>

      {/* Agent Status */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">AI Agents Status</h3>
          <p className="mt-1 text-sm text-gray-500">
            Multi-agent system for content analysis and echo chamber detection
          </p>
        </div>

        <div className="px-6 py-4">
          <div className="space-y-4">
            {displayAgents.map((agent: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(agent.status)}
                  <div>
                    <h4 className="text-sm font-medium text-gray-900">{agent.name}</h4>
                    <p className="text-xs text-gray-500">{agent.description}</p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-900 font-medium">
                    {agent.capabilities} capabilities
                  </div>
                  <div className={`text-xs capitalize ${
                    agent.status === 'healthy' ? 'text-green-600' :
                    agent.status === 'unhealthy' ? 'text-red-600' : 'text-yellow-600'
                  }`}>
                    {agent.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* API Endpoints */}
      {systemInfo && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Available Endpoints</h3>
          </div>

          <div className="px-6 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(systemInfo.endpoints).map(([name, path]) => (
                <div key={name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm font-medium text-gray-900 capitalize">{name}</span>
                  <code className="text-xs text-gray-600 bg-white px-2 py-1 rounded border">
                    {path}
                  </code>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}