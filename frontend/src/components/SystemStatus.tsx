'use client';

import { useState, useEffect } from 'react';
import { apiService } from '@/lib/api';
import { CheckCircle, XCircle, AlertCircle, RefreshCw, Activity, Cpu, Database, Zap, ChevronDown, CheckCircle2 } from 'lucide-react';

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
  capabilitiesList?: string[];
}

export default function SystemStatus() {
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [lastCheck, setLastCheck] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agentsData, setAgentsData] = useState<AgentInfo[]>([]);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  // Current system architecture - Pure RAG with LangGraph orchestration
  const fallbackAgents: LegacyAgentInfo[] = [
    {
      name: 'RAG System',
      status: 'healthy',
      capabilities: 8,
      description: 'Pure vector-based Retrieval Augmented Generation system',
      capabilitiesList: [
        'OpenAI text-embedding-3-small (1536 dimensions)',
        'pgvector cosine similarity search',
        'Semantic search across ProcessedContent, Insights, PainPoints, Threads',
        'Query intent classification (conversational, semantic, hybrid)',
        'Conversational query rewriting with context',
        'Configurable similarity thresholds (0.3-0.5)',
        'LangSmith tracing and monitoring',
        'Greeting/chitchat detection and handling'
      ]
    },
    {
      name: 'LangGraph Orchestrator',
      status: 'healthy',
      capabilities: 6,
      description: 'StateGraph-based workflow orchestration and agent coordination',
      capabilitiesList: [
        'Campaign workflow management',
        'Chat workflow with conversation history',
        'Parallel task execution',
        'State management and persistence',
        'Error handling and retry mechanisms',
        'Compliance tracking and audit trails'
      ]
    },
    {
      name: 'Scout Agent',
      status: 'healthy',
      capabilities: 5,
      description: 'Reddit data collection and community discovery',
      capabilitiesList: [
        'PRAW Reddit API integration',
        'Subreddit search and filtering',
        'Thread and comment scraping',
        'Real-time data collection',
        'Community metadata extraction'
      ]
    },
    {
      name: 'Analyst Agent',
      status: 'healthy',
      capabilities: 7,
      description: 'GPT-4 powered content analysis and insight generation',
      capabilitiesList: [
        'Sentiment analysis (positive/negative scoring)',
        'Pain point extraction and categorization',
        'Keyword and topic extraction',
        'Strategic report generation',
        'Content summarization',
        'Insight validation and confidence scoring',
        'Campaign performance analysis'
      ]
    },
    {
      name: 'Embedding Service',
      status: 'healthy',
      capabilities: 4,
      description: 'Vector embedding generation and management',
      capabilitiesList: [
        'Batch embedding generation',
        'ProcessedContent embedding',
        'Insight (strategic reports) embedding',
        'PainPoint embedding with context'
      ]
    },
    {
      name: 'Monitoring & Guardrails',
      status: 'healthy',
      capabilities: 5,
      description: 'LangSmith integration and content safety',
      capabilitiesList: [
        'LangSmith tracing for all LLM calls',
        'Query validation and sanitization',
        'Output safety checks',
        'Token usage and cost tracking',
        'Performance monitoring'
      ]
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
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/api/v1/admin/agents/status/`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Transform the new API format to our component format
        if (data.agents && Array.isArray(data.agents)) {
          const transformedAgents: LegacyAgentInfo[] = data.agents.map((agent: any) => ({
            name: agent.name,
            status: agent.status,
            capabilities: agent.capabilities,
            description: agent.description,
            capabilitiesList: [] // Will use the expanded format from fallbackAgents
          }));
          
          // Merge with fallback data to get capabilitiesList
          const mergedAgents = transformedAgents.map(apiAgent => {
            const fallbackAgent = fallbackAgents.find(fa => fa.name === apiAgent.name);
            return {
              ...apiAgent,
              capabilitiesList: fallbackAgent?.capabilitiesList || []
            };
          });
          
          // Update fallback agents with live status
          fallbackAgents.forEach(agent => {
            const liveAgent = mergedAgents.find(ma => ma.name === agent.name);
            if (liveAgent) {
              agent.status = liveAgent.status;
            }
          });
        }
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
    <div className="w-full space-y-6">
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
          <h3 className="text-lg font-medium text-gray-900">AI Agents and Services - Status</h3>
          <p className="mt-1 text-sm text-gray-500">
            Multi-agent system for content analysis and echo chamber detection
          </p>
        </div>

        <div className="px-6 py-4">
          <div className="space-y-4">
            {displayAgents.map((agent: any, index: number) => (
              <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedAgent(expandedAgent === agent.name ? null : agent.name)}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(agent.status)}
                    <div className="text-left">
                      <h4 className="text-sm font-medium text-gray-900">{agent.name}</h4>
                      <p className="text-xs text-gray-500">{agent.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-right">
                      <div className="text-sm text-gray-900 font-medium">
                        {agent.capabilitiesList?.length || agent.capabilities} capabilities
                      </div>
                      <div className={`text-xs capitalize ${
                        agent.status === 'healthy' ? 'text-green-600' :
                        agent.status === 'unhealthy' ? 'text-red-600' : 'text-yellow-600'
                      }`}>
                        {agent.status}
                      </div>
                    </div>
                    <ChevronDown 
                      className={`w-5 h-5 text-gray-400 transition-transform ${
                        expandedAgent === agent.name ? 'transform rotate-180' : ''
                      }`}
                    />
                  </div>
                </button>
                
                {expandedAgent === agent.name && agent.capabilitiesList && (
                  <div className="px-4 pb-4 bg-gray-50">
                    <div className="pt-3 border-t border-gray-200">
                      <h5 className="text-xs font-medium text-gray-700 mb-2">Capabilities:</h5>
                      <ul className="space-y-2">
                        {agent.capabilitiesList.map((capability: string, capIndex: number) => (
                          <li key={capIndex} className="flex items-start space-x-2">
                            <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                            <span className="text-xs text-gray-700">{capability}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}