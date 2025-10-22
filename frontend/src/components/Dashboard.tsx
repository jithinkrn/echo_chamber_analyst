'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Users, MessageSquare, AlertTriangle, Building, ChevronDown } from 'lucide-react';

// Simple Card components
const Card = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`bg-white overflow-hidden shadow rounded-lg ${className}`}>
    {children}
  </div>
);

const CardHeader = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`px-4 py-2 ${className}`}>
    {children}
  </div>
);

const CardTitle = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <h3 className={`text-lg font-medium leading-6 text-gray-900 ${className}`}>
    {children}
  </h3>
);

const CardContent = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`px-4 py-2 ${className}`}>
    {children}
  </div>
);

interface Brand {
  id: string;
  name: string;
  description: string;
  industry: string;
  campaign_count: number;
}

interface DashboardData {
  brand?: {
    id: string;
    name: string;
    description: string;
  };
  kpis: {
    active_campaigns: number;
    high_echo_communities: number;
    high_echo_change_percent: number;
    new_pain_points_above_50: number;
    new_pain_points_change: number;
    positivity_ratio: number;
    positivity_change_pp: number;
    llm_tokens_used: number;
    llm_cost_usd: number;
  };
  heatmap: Array<{
    name: string;
    platform: string;
    echo_score: number;
    echo_score_change: number;
    pain_points: Array<{
      keyword: string;
      growth_percentage: number;
      heat_level: number;
    }>;
  }>;
  top_pain_points: Array<{
    keyword: string;
    growth_percentage: number;
    mention_count: number;
  }>;
  community_watchlist: Array<{
    rank: number;
    name: string;
    echo_score: number;
    echo_change: number;
    new_threads: number;
    key_influencer: string;
  }>;
  influencer_pulse: Array<{
    handle: string;
    platform: string;
    reach: number;
    engagement_rate: number;
    topics_text: string;
  }>;
  filters: {
    date_range: string;
    brand: string;
    sources: string[];
  };
  campaign_analytics?: {
    total_campaigns: number;
    active_campaigns: number;
    completed_campaigns: number;
    paused_campaigns: number;
    total_budget: number;
    total_spent: number;
    budget_utilization: number;
  };
}

interface ThreadDetailData {
  thread_id: string;
  title: string;
  content: string;
  comment_count: number;
  echo_score: number;
  sentiment_score: number;
  llm_summary: string;
  token_count: number;
  created_at: string;
  pain_point_chips: string[];
  influencer_mentions: Array<{
    handle: string;
    karma_score: number;
  }>;
  community_name: string;
  community_platform: string;
}

export default function Dashboard() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrand, setSelectedBrand] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [dataLoading, setDataLoading] = useState(false); // Separate loading state for data refresh
  const [selectedThread, setSelectedThread] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showBrandDropdown, setShowBrandDropdown] = useState(false);

  useEffect(() => {
    fetchBrands();
  }, []);

  useEffect(() => {
    if (selectedBrand) {
      fetchDashboardData();
    }
  }, [selectedBrand]);

  const fetchBrands = async () => {
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const response = await fetch(`${API_BASE_URL}/brands/`);
      if (response.ok) {
        const data = await response.json();
        setBrands(data.results || []);
        // Auto-select first brand if available and no brand is currently selected
        if (data.results && data.results.length > 0 && !selectedBrand) {
          setSelectedBrand(data.results[0].id);
        }
      }
    } catch (error) {
      console.error('Error fetching brands:', error);
      // Mock brands for development
      const mockBrands = [
        { id: '1', name: 'BreezyCool', description: 'Sustainable cooling solutions', industry: 'Home Appliances', campaign_count: 3 },
        { id: '2', name: 'TechFlow', description: 'Smart home automation', industry: 'Technology', campaign_count: 2 }
      ];
      setBrands(mockBrands);
      if (!selectedBrand) {
        setSelectedBrand('1');
      }
    }
  };

  const fetchDashboardData = async () => {
    if (!selectedBrand) {
      console.log('No brand selected, skipping dashboard data fetch');
      return;
    }

    try {
      // Use dataLoading for brand switches, loading for initial load
      if (dashboardData) {
        setDataLoading(true);
      } else {
        setLoading(true);
      }
      
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const url = `${API_BASE_URL}/dashboard/overview/brand/?brand_id=${selectedBrand}`;
      console.log('Fetching dashboard data from:', url);
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Failed to fetch dashboard data');
      }
      
      const data = await response.json();
      console.log('Received dashboard data:', data);
      setDashboardData(data);
      setError(null);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
      setDataLoading(false);
    }
  };

  const getHeatLevelDots = (level: number) => {
    return Array.from({ length: Math.min(level, 5) }).map((_, i) => (
      <span key={i} className="text-red-500 text-sm">⬤</span>
    ));
  };

  const formatReach = (reach: number) => {
    if (reach >= 1000) {
      return `${(reach / 1000).toFixed(0)}k`;
    }
    return reach.toString();
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-48 mb-6"></div>
          <div className="grid grid-cols-5 gap-4 mb-6">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-6">
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error Loading Dashboard</h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
              <div className="mt-4">
                <button
                  onClick={fetchDashboardData}
                  className="bg-red-100 text-red-800 px-3 py-1 rounded text-sm hover:bg-red-200"
                >
                  Try Again
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return <div className="p-6">No dashboard data available</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Dashboard Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <div className="flex gap-4 items-center">
          <div className="text-sm text-gray-600">
            {dashboardData?.filters?.date_range || 'September 2025'}
          </div>
          <div className="text-sm text-gray-600">
            Brand: {dashboardData?.brand?.name || dashboardData?.filters?.brand || (selectedBrand ? brands.find(b => b.id === selectedBrand)?.name : 'All Brands')}
          </div>
          <div className="text-sm text-gray-600">
            Source: {dashboardData?.filters?.sources?.join(' + ') || 'Reddit + Discord + TikTok'}
          </div>
        </div>
      </div>

      {/* Brand Selector */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">Brand Analytics</h2>
            <div className="flex items-center space-x-3">
              {dataLoading && (
                <div className="flex items-center text-blue-600">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  <span className="ml-2 text-sm">Loading data...</span>
                </div>
              )}
              <div className="relative">
                <button
                  onClick={() => setShowBrandDropdown(!showBrandDropdown)}
                  className="flex items-center space-x-2 px-4 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <Building className="h-4 w-4" />
                  <span>
                    {selectedBrand ? brands.find(b => b.id === selectedBrand)?.name || 'Select Brand' : 'Select Brand'}
                  </span>
                  <ChevronDown className="h-4 w-4" />
                </button>
                
                {showBrandDropdown && (
                  <div className="absolute right-0 mt-2 w-64 bg-white border border-gray-200 rounded-md shadow-lg z-10">
                    <div className="p-2">
                      {brands.map((brand) => (
                        <button
                          key={brand.id}
                          onClick={() => {
                            console.log('Brand selection changed to:', brand.name, brand.id);
                            setSelectedBrand(brand.id);
                            setShowBrandDropdown(false);
                          }}
                          className={`w-full text-left px-3 py-2 rounded-md text-sm ${
                            selectedBrand === brand.id
                              ? 'bg-blue-100 text-blue-900'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          <div className="font-medium">{brand.name}</div>
                          <div className="text-xs text-gray-500">{brand.industry} • {brand.campaign_count} campaigns</div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Active Campaigns
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">
              {dashboardData.kpis.active_campaigns}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              High‑Echo Communities
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">
              {dashboardData.kpis.high_echo_communities}
            </div>
            <div className="flex items-center text-sm text-green-600">
              <TrendingUp className="h-4 w-4 mr-1" />
              +{dashboardData.kpis.high_echo_change_percent}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              New Pain‑pts &gt; +50%
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">
              {dashboardData.kpis.new_pain_points_above_50}
            </div>
            <div className="flex items-center text-sm text-green-600">
              <TrendingUp className="h-4 w-4 mr-1" />
              +{dashboardData.kpis.new_pain_points_change}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Positivity Ratio
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">
              {dashboardData.kpis.positivity_ratio}% 😊
            </div>
            <div className="flex items-center text-sm text-red-600">
              <TrendingDown className="h-4 w-4 mr-1" />
              {dashboardData.kpis.positivity_change_pp} pp
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              LLM Tokens Burnt
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-900">
              {dashboardData.kpis.llm_tokens_used}k
            </div>
            <div className="flex items-center text-sm text-gray-600">
              <DollarSign className="h-4 w-4 mr-1" />
              ${dashboardData.kpis.llm_cost_usd}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Heat Map and Top Pain Points */}
      <div className="grid grid-cols-2 gap-6">
        {/* Community Heat Map */}
        <Card>
          <CardHeader>
            <CardTitle>HEAT‑MAP: Where the talk is</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-xs font-medium text-gray-600 border-b pb-2">
                <span>Community ▼</span>
                <span>Pain Point ▲</span>
              </div>
              {(dashboardData.heatmap || []).length > 0 ? (
                (dashboardData.heatmap || []).slice(0, 4).map((community, index) => (
                  <div key={index} className="grid grid-cols-2 gap-4 items-center">
                    <div className="font-medium text-sm text-gray-900">
                      {community.name}
                    </div>
                    <div className="flex items-center justify-between">
                      {(community.pain_points || []).slice(0, 1).map((pp, ppIndex) => (
                        <div key={ppIndex} className="flex items-center gap-2">
                          <div className="flex">
                            {getHeatLevelDots(pp.heat_level)}
                          </div>
                          <span className="text-sm text-gray-700">
                            {pp.keyword} (+{pp.growth_percentage}%)
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-8">
                  <p className="text-sm">No community heat map data available for this brand</p>
                  <p className="text-xs mt-1">Try selecting "All Brands" or check back later</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Top Growing Pains */}
        <Card>
          <CardHeader>
            <CardTitle>TOP‑GROWING PAINS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(dashboardData.top_pain_points || []).length > 0 ? (
                (dashboardData.top_pain_points || []).slice(0, 3).map((painPoint, index) => (
                  <div key={index} className="flex justify-between items-center">
                    <span className="text-sm text-gray-900">
                      {index + 1}. {painPoint.keyword}
                    </span>
                    <div className="flex items-center text-sm text-green-600">
                      <TrendingUp className="h-4 w-4 mr-1" />
                      +{painPoint.growth_percentage}%
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-4">
                  <p className="text-sm">No pain points data available for this brand</p>
                  <p className="text-xs mt-1">Try selecting a different brand or check back later</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Community Watchlist and Influencer Pulse */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>COMMUNITY WATCHLIST</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="grid grid-cols-6 gap-2 text-xs font-medium text-gray-600 border-b pb-2">
                <span>Rank</span>
                <span>Echo</span>
                <span>Δ</span>
                <span>New Threads</span>
                <div className="col-span-2">Key Influencer</div>
              </div>
              {(dashboardData.community_watchlist || []).slice(0, 3).map((community, index) => (
                <div key={index} className="grid grid-cols-6 gap-2 text-sm items-center">
                  <span className="font-medium">{community.rank}</span>
                  <span className="text-gray-700">{community.echo_score.toFixed(1)}</span>
                  <div className="flex items-center text-green-600">
                    <TrendingUp className="h-3 w-3 mr-1" />
                    {community.echo_change}%
                  </div>
                  <span className="text-gray-700">{community.new_threads}</span>
                  <div className="col-span-2 text-gray-900 truncate">
                    {community.key_influencer}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>INFLUENCER PULSE (&lt;50k)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="grid grid-cols-4 gap-2 text-xs font-medium text-gray-600 border-b pb-2">
                <span>Handle</span>
                <span>Reach</span>
                <span>Eng%</span>
                <span>Talks about…</span>
              </div>
              {(dashboardData.influencer_pulse || []).slice(0, 3).map((influencer, index) => (
                <div key={index} className="grid grid-cols-4 gap-2 text-sm items-center">
                  <span className="font-medium text-gray-900">{influencer.handle}</span>
                  <span className="text-gray-700">{formatReach(influencer.reach)}</span>
                  <span className="text-gray-700">{influencer.engagement_rate.toFixed(1)}</span>
                  <span className="text-xs text-gray-600 truncate">
                    {influencer.topics_text}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Campaign Analytics Section */}
      {selectedBrand && dashboardData?.campaign_analytics && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Campaign Analytics</h2>
            <p className="text-sm text-gray-600">Performance metrics for {brands.find((b: Brand) => b.id === selectedBrand)?.name} campaigns</p>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <TrendingUp className="h-8 w-8 text-blue-600" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Total Campaigns</p>
                    <p className="text-2xl font-semibold text-gray-900">{dashboardData?.campaign_analytics?.total_campaigns}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <Users className="h-8 w-8 text-green-600" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Active Campaigns</p>
                    <p className="text-2xl font-semibold text-gray-900">{dashboardData?.campaign_analytics?.active_campaigns}</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-yellow-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <DollarSign className="h-8 w-8 text-yellow-600" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Budget Utilization</p>
                    <p className="text-2xl font-semibold text-gray-900">{dashboardData?.campaign_analytics?.budget_utilization}%</p>
                  </div>
                </div>
              </div>
              
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="flex items-center">
                  <Users className="h-8 w-8 text-purple-600" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Completed</p>
                    <p className="text-2xl font-semibold text-gray-900">{dashboardData?.campaign_analytics?.completed_campaigns}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-sm font-medium text-gray-900 mb-3">Budget Overview</h3>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Total Budget:</span>
                    <span className="font-medium">${dashboardData?.campaign_analytics?.total_budget?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Total Spent:</span>
                    <span className="font-medium">${dashboardData?.campaign_analytics?.total_spent?.toFixed(2) || '0.00'}</span>
                  </div>
                  <div className="mt-2">
                    <div className="bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{
                          width: `${Math.min(dashboardData?.campaign_analytics?.budget_utilization || 0, 100)}%`
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-sm font-medium text-gray-900 mb-3">Campaign Status</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Active</span>
                    <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                      {dashboardData?.campaign_analytics?.active_campaigns}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Paused</span>
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                      {dashboardData?.campaign_analytics?.paused_campaigns || 0}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Completed</span>
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                      {dashboardData?.campaign_analytics?.completed_campaigns}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      {selectedThread && (
        <ThreadDetailModal
          threadId={selectedThread}
          onClose={() => setSelectedThread(null)}
        />
      )}
    </div>
  );
}

// Thread Detail Modal Component
function ThreadDetailModal({ threadId, onClose }: { threadId: string; onClose: () => void }) {
  const [threadData, setThreadData] = useState<ThreadDetailData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchThreadDetail();
  }, [threadId]);

  const fetchThreadDetail = async () => {
    try {
      setLoading(true);
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const response = await fetch(`${API_BASE_URL}/threads/${threadId}/`);
      
      if (!response.ok) {
        throw new Error('Thread not found');
      }
      
      const data = await response.json();
      setThreadData(data);
    } catch (error) {
      console.error('Error fetching thread detail:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-4xl max-h-[80vh] overflow-y-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!threadData) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-4xl">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Thread Not Found</h2>
            <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
              ✕
            </button>
          </div>
          <p>The requested thread could not be found.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-4xl max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Thread Detail Modal</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 text-xl">
            ✕
          </button>
        </div>
        
        <div className="space-y-4">
          <div className="border-b pb-4">
            <h3 className="font-medium text-lg">
              {threadData.community_name} | Thread #{threadData.thread_id} — {threadData.comment_count} comments
            </h3>
          </div>
          
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-2">
                📝 LLM Summary ({threadData.token_count} tokens)
              </h4>
              <p className="text-sm text-gray-700 mb-4 p-3 bg-gray-50 rounded">
                "{threadData.llm_summary}"
              </p>
              
              <div className="mb-4">
                <span className="text-sm font-medium">Pain-point chips: </span>
                <div className="flex flex-wrap gap-2 mt-2">
                  {threadData.pain_point_chips?.map((chip, index) => (
                    <span key={index} className="inline-block bg-blue-100 text-blue-800 rounded-full px-3 py-1 text-xs">
                      {chip}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mb-4">
                <span className="text-sm font-medium">Quote: </span>
                <p className="text-sm text-gray-600 italic mt-1">
                  "{threadData.content.substring(0, 150)}..."
                </p>
              </div>
            </div>
            
            <div>
              <h4 className="font-medium mb-2">Metrics</h4>
              <div className="text-sm space-y-2 bg-gray-50 p-3 rounded">
                <div className="flex justify-between">
                  <span>Sentiment:</span>
                  <span className="font-medium">+42/-31</span>
                </div>
                <div className="flex justify-between">
                  <span>EchoScore:</span>
                  <span className="font-medium">{threadData.echo_score}</span>
                </div>
                <div className="flex justify-between">
                  <span>Tokens:</span>
                  <span className="font-medium">{threadData.token_count}</span>
                </div>
                <div className="flex justify-between">
                  <span>Age:</span>
                  <span className="font-medium">
                    {new Date(threadData.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              <div className="mt-4">
                <h4 className="font-medium mb-2">Influence Graph</h4>
                {threadData.influencer_mentions?.map((inf, index) => (
                  <div key={index} className="text-sm">
                    {inf.handle} ({inf.karma_score} karma)
                  </div>
                ))}
              </div>

              <div className="mt-4 space-y-2">
                <button className="w-full bg-blue-600 text-white py-2 px-4 rounded text-sm hover:bg-blue-700">
                  DM {threadData.influencer_mentions?.[0]?.handle || 'Influencer'}
                </button>
                <button className="w-full bg-gray-200 text-gray-800 py-2 px-4 rounded text-sm hover:bg-gray-300">
                  Re‑summarise
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
