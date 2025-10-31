'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Users, MessageSquare, AlertTriangle, Building, ChevronDown, Lightbulb, Target, X } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter, ZAxis, Cell } from 'recharts';
import { apiService } from '@/lib/api';

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
  heatmap: {
    community_pain_point_matrix?: Array<{
      community_name: string;
      platform: string;
      echo_score: number;
      pain_points: Array<{
        keyword: string;
        mention_count: number;
        heat_level: number;
        sentiment_score: number;
        growth_percentage: number;
      }>;
    }>;
    time_series_pain_points?: Array<{
      keyword: string;
      growth_rate: number;
      total_mentions: number;
      time_series: Array<{
        date: string;
        label: string;
        mention_count: number;
        sentiment_score: number;
        heat_level: number;
      }>;
    }>;
    total_mentions_series?: Array<{
      date: string;
      label: string;
      total_mentions: number;
    }>;
  };
  top_pain_points: Array<{
    keyword: string;
    growth_percentage: number;
    mention_count: number;
  }>;
  community_watchlist: Array<{
    rank: number;
    name: string;
    platform: string;
    member_count: number;
    echo_score: number;
    echo_change: number;
    new_threads: number;
    activity_score: number;
    threads_last_4_weeks: number;
    avg_engagement_rate: number;
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
  const [selectedCommunity, setSelectedCommunity] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [showBrandDropdown, setShowBrandDropdown] = useState(false);
  const [analysisSummary, setAnalysisSummary] = useState<any>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  // NEW: Modal states for threads and influencers
  const [showThreadsModal, setShowThreadsModal] = useState(false);
  const [showInfluencersModal, setShowInfluencersModal] = useState(false);
  const [communityThreads, setCommunityThreads] = useState<any[]>([]);
  const [communityInfluencers, setCommunityInfluencers] = useState<any[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(false);
  const [influencersLoading, setInfluencersLoading] = useState(false);

  useEffect(() => {
    fetchBrands();
  }, []);

  useEffect(() => {
    if (selectedBrand) {
      fetchDashboardData();
      fetchAnalysisSummary();
    }
  }, [selectedBrand]);

  const fetchBrands = async () => {
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/api/v1/brands/`);
      if (response.ok) {
        const data = await response.json();
        setBrands(data.results || []);
        // Auto-select first brand if available and no brand is currently selected
        if (data.results && data.results.length > 0 && !selectedBrand) {
          setSelectedBrand(data.results[0].id);
        } else if (!data.results || data.results.length === 0) {
          // No brands available - stop loading to show empty state
          setLoading(false);
        }
      }
    } catch (error) {
      console.error('Error fetching brands:', error);
      setBrands([]);
      setLoading(false);
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

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const url = `${API_BASE_URL}/api/v1/dashboard/overview/brand/?brand_id=${selectedBrand}`;
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

  const fetchAnalysisSummary = async () => {
    if (!selectedBrand) return;

    try {
      setSummaryLoading(true);
      const data = await apiService.getBrandAnalysisSummary(selectedBrand);
      if (data.summary) {
        setAnalysisSummary(data.summary);
      } else {
        setAnalysisSummary(null);
      }
    } catch (error) {
      console.error('Error fetching analysis summary:', error);
      setAnalysisSummary(null);
    } finally {
      setSummaryLoading(false);
    }
  };

  // NEW: Fetch threads for selected community
  const fetchCommunityThreads = async (communityName: string) => {
    if (!selectedBrand) return;

    try {
      setThreadsLoading(true);
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const url = `${API_BASE_URL}/api/threads/?brand=${selectedBrand}&community=${encodeURIComponent(communityName)}`;

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch threads');
      }

      const data = await response.json();
      setCommunityThreads(data.threads || []);
      setShowThreadsModal(true);
    } catch (error) {
      console.error('Error fetching community threads:', error);
      setCommunityThreads([]);
    } finally {
      setThreadsLoading(false);
    }
  };

  // NEW: Fetch influencers for selected community
  const fetchCommunityInfluencers = async (communityName: string) => {
    if (!selectedBrand) return;

    try {
      setInfluencersLoading(true);
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const url = `${API_BASE_URL}/api/brands/${selectedBrand}/influencers/?community=${encodeURIComponent(communityName)}`;

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch influencers');
      }

      const data = await response.json();
      setCommunityInfluencers(data.influencers || []);
      setShowInfluencersModal(true);
    } catch (error) {
      console.error('Error fetching community influencers:', error);
      setCommunityInfluencers([]);
    } finally {
      setInfluencersLoading(false);
    }
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

  // Empty state when no brands exist
  if (!loading && brands.length === 0) {
    return (
      <div className="p-6">
        <div className="bg-white shadow rounded-lg p-12">
          <div className="text-center">
            <Building className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-lg font-medium text-gray-900">No Brands Yet</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating your first brand to begin tracking echo chamber analytics.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Empty state when brand has no data
  if (!dashboardData) {
    return (
      <div className="p-6">
        <div className="bg-white shadow rounded-lg p-12">
          <div className="text-center">
            <Target className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-lg font-medium text-gray-900">No Data Available Yet</h3>
            <p className="mt-1 text-sm text-gray-500">
              This brand doesn't have any analysis data yet. Create a campaign and run scout analysis to start collecting insights.
            </p>
          </div>
        </div>
      </div>
    );
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
            <div className="flex items-center text-sm text-green-600 mb-3">
              <TrendingUp className="h-4 w-4 mr-1" />
              +{dashboardData.kpis.high_echo_change_percent}%
            </div>
            <div className="space-y-1 text-xs">
              {(dashboardData.community_watchlist || []).slice(0, 2).map((community, index) => (
                <div key={index} className="flex justify-between items-center">
                  <span className="text-gray-700 truncate">{community.name}</span>
                  <span className="text-gray-900 font-medium">{community.echo_score.toFixed(1)}</span>
                </div>
              ))}
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
            <div className="flex items-center text-sm text-green-600 mb-3">
              <TrendingUp className="h-4 w-4 mr-1" />
              +{dashboardData.kpis.new_pain_points_change}
            </div>
            <div className="space-y-1 text-xs">
              {(dashboardData.top_pain_points || []).slice(0, 3).map((pp, index) => (
                <div key={index} className="flex justify-between items-center">
                  <span className="text-gray-700 truncate">{pp.keyword}</span>
                  <span className="text-green-600 font-medium">+{pp.growth_percentage.toFixed(0)}%</span>
                </div>
              ))}
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
            <div className="flex items-center text-sm text-red-600 mb-3">
              <TrendingDown className="h-4 w-4 mr-1" />
              {dashboardData.kpis.positivity_change_pp} pp
            </div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-green-700">😊 Positive</span>
                <span className="text-green-900 font-medium">{dashboardData.kpis.positivity_ratio}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-red-700">😞 Negative</span>
                <span className="text-red-900 font-medium">{(100 - dashboardData.kpis.positivity_ratio).toFixed(0)}%</span>
              </div>
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
        {/* Top Growing Pains */}
        <Card>
          <CardHeader>
            <CardTitle>TOP‑GROWING PAINS</CardTitle>
          </CardHeader>
          <CardContent>
            {(dashboardData.top_pain_points || []).length > 0 ? (
              (() => {
                const painPoints = dashboardData.top_pain_points || [];
                const chartHeight = Math.max(350, painPoints.length * 65);
                const barColors = [
                  '#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6',
                  '#8b5cf6', '#ec4899', '#06b6d4', '#f43f5e', '#84cc16',
                ];
                return (
                  <ResponsiveContainer width="100%" height={chartHeight}>
                    <BarChart data={painPoints} layout="vertical" margin={{ top: 5, right: 15, left: 5, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis type="number" stroke="#6b7280" style={{ fontSize: '10px' }} tick={{ dy: 5 }} />
                      <YAxis type="category" dataKey="keyword" stroke="#6b7280" style={{ fontSize: '10px' }} width={110} tick={{ dx: -5 }} />
                      <Tooltip cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const data = payload[0].payload;
                            return (
                              <div className="bg-white p-3 border border-gray-200 rounded shadow-lg text-xs">
                                <p className="font-bold text-gray-900">{data.keyword}</p>
                                <p className="text-gray-700">Growth: <span className="font-medium text-green-600">+{data.growth_percentage.toFixed(1)}%</span></p>
                                <p className="text-gray-700">Mentions: <span className="font-medium">{data.mention_count}</span></p>
                              </div>
                            );
                          }
                          return null;
                        }} />
                      <Bar dataKey="growth_percentage" radius={[0, 4, 4, 0]}
                        label={{ position: 'right', formatter: (value: any) => `+${Number(value).toFixed(0)}%`,
                          style: { fontSize: '11px', fontWeight: 'bold' } }}>
                        {painPoints.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={barColors[index % barColors.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                );
              })()
            ) : (
              <div className="text-center text-gray-500 py-4">
                <p className="text-sm">No pain points data available for this brand</p>
                <p className="text-xs mt-1">Try selecting a different brand or check back later</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Community × Pain Point Bubble Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Communities × Pain Points</CardTitle>
          </CardHeader>
          <CardContent>
            {(dashboardData.heatmap?.community_pain_point_matrix || []).length > 0 ? (
              (() => {
                const communities = dashboardData.heatmap?.community_pain_point_matrix || [];
                const painPointColors = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899', '#06b6d4'];
                const chartData: any[] = [];
                const painPointsSet = new Set<string>();
                communities.forEach((community, commIdx) => {
                  (community.pain_points || []).forEach((pp, ppIdx) => {
                    painPointsSet.add(pp.keyword);
                    chartData.push({
                      community: community.community_name, communityIndex: commIdx,
                      painPoint: pp.keyword, painPointIndex: ppIdx,
                      mentions: pp.mention_count, sentiment: pp.sentiment_score,
                      growth: pp.growth_percentage
                    });
                  });
                });
                const painPointsList = Array.from(painPointsSet);
                const painPointColorMap: Record<string, string> = {};
                painPointsList.forEach((pp, idx) => {
                  painPointColorMap[pp] = painPointColors[idx % painPointColors.length];
                });
                return (
                  <div className="space-y-2">
                    <ResponsiveContainer width="100%" height={400}>
                      <ScatterChart margin={{ top: 10, right: 10, left: 10, bottom: 60 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis type="category" dataKey="community" name="Community" allowDuplicatedCategory={false}
                          stroke="#6b7280" angle={-45} textAnchor="end" height={60} interval={0} style={{ fontSize: '11px' }} />
                        <YAxis type="category" dataKey="painPoint" name="Pain Point" allowDuplicatedCategory={false}
                          stroke="#6b7280" style={{ fontSize: '11px' }} width={100} />
                        <ZAxis type="number" dataKey="mentions" range={[200, 2000]} name="Mentions" />
                        <Tooltip cursor={{ strokeDasharray: '3 3' }}
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const data = payload[0].payload;
                              return (
                                <div className="bg-white p-3 border border-gray-200 rounded shadow-lg text-xs">
                                  <p className="font-bold text-gray-900">{data.community}</p>
                                  <p className="text-gray-700">Pain Point: <span className="font-medium">{data.painPoint}</span></p>
                                  <p className="text-gray-700">Mentions: <span className="font-medium">{data.mentions}</span></p>
                                  <p className="text-gray-700">Growth: <span className="font-medium text-green-600">+{data.growth.toFixed(1)}%</span></p>
                                  <p className="text-gray-700">Sentiment: <span className="font-medium">{data.sentiment.toFixed(2)}</span></p>
                                </div>
                              );
                            }
                            return null;
                          }} />
                        <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '5px' }}
                          content={() => (
                            <div className="flex flex-wrap justify-center gap-2 mt-2">
                              {painPointsList.map((pp, idx) => (
                                <div key={idx} className="flex items-center gap-1">
                                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: painPointColorMap[pp] }} />
                                  <span className="text-xs text-gray-700">{pp}</span>
                                </div>
                              ))}
                            </div>
                          )} />
                        {painPointsList.map((painPoint) => {
                          const ppData = chartData.filter(d => d.painPoint === painPoint);
                          return (
                            <Scatter key={painPoint} name={painPoint} data={ppData} fill={painPointColorMap[painPoint]}
                              shape={(props: any) => {
                                const { cx, cy, fill, payload } = props;
                                const radius = Math.sqrt(payload.mentions) * 2.5;
                                return (
                                  <g>
                                    <circle cx={cx} cy={cy} r={radius} fill={fill} opacity={0.8} />
                                    <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle"
                                      fill="white" fontSize="11" fontWeight="bold">{payload.mentions}</text>
                                  </g>
                                );
                              }} />
                          );
                        })}
                      </ScatterChart>
                    </ResponsiveContainer>
                    <div className="text-xs text-gray-500 text-center">
                      Bubble size and number indicate mention count • Hover for details
                    </div>
                  </div>
                );
              })()
            ) : (
              <div className="text-center text-gray-500 py-8">
                <p className="text-sm">No community heat map data available for this brand</p>
                <p className="text-xs mt-1">Run a campaign to collect data</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Pain Point Trends Line Chart */}
      <Card>
        <CardHeader>
          <CardTitle>PAIN POINT TRENDS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {(dashboardData.heatmap?.time_series_pain_points || []).length > 0 ? (
              <>
                <div className="text-xs text-gray-600 mb-3">
                  Last 4 weeks • Tracking mention trends for top pain points
                </div>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart
                    data={(() => {
                      // Transform data for line chart
                      const painPoints = dashboardData.heatmap?.time_series_pain_points || [];
                      const totalSeries = dashboardData.heatmap?.total_mentions_series || [];

                      if (painPoints.length === 0) return [];

                      // Get weeks from first pain point
                      const weeks = painPoints[0]?.time_series || [];

                      // Create chart data with week on x-axis and all pain points as separate lines
                      return weeks.map((weekData, idx) => {
                        const dataPoint: any = {
                          week: weekData.label,
                          dateRange: weekData.date,
                          Total: totalSeries[idx]?.total_mentions || 0
                        };

                        // Add each pain point as a separate line
                        painPoints.forEach((pp) => {
                          dataPoint[pp.keyword] = pp.time_series[idx]?.mention_count || 0;
                        });

                        return dataPoint;
                      });
                    })()}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="week"
                      stroke="#6b7280"
                      style={{ fontSize: '12px' }}
                    />
                    <YAxis
                      stroke="#6b7280"
                      style={{ fontSize: '12px' }}
                      label={{ value: 'Mentions', angle: -90, position: 'insideLeft', style: { fontSize: '12px', fill: '#6b7280' } }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '6px',
                        fontSize: '12px'
                      }}
                      labelFormatter={(label) => {
                        const dataPoint = (dashboardData.heatmap?.time_series_pain_points?.[0]?.time_series || []).find((d: any) => d.label === label);
                        return dataPoint ? `${label} (${dataPoint.date})` : label;
                      }}
                    />
                    <Legend
                      wrapperStyle={{ fontSize: '12px' }}
                      iconType="line"
                    />
                    {/* Total line - bold and dark */}
                    <Line
                      type="monotone"
                      dataKey="Total"
                      stroke="#1f2937"
                      strokeWidth={3}
                      dot={{ r: 5 }}
                      activeDot={{ r: 7 }}
                    />
                    {/* Individual pain point lines - different colors */}
                    {(dashboardData.heatmap?.time_series_pain_points || []).map((pp, idx) => {
                      const colors = ['#ef4444', '#f97316', '#eab308', '#84cc16', '#06b6d4'];
                      return (
                        <Line
                          key={pp.keyword}
                          type="monotone"
                          dataKey={pp.keyword}
                          stroke={colors[idx % colors.length]}
                          strokeWidth={2}
                          dot={{ r: 4 }}
                          activeDot={{ r: 6 }}
                        />
                      );
                    })}
                  </LineChart>
                </ResponsiveContainer>
                {/* Legend with growth rates */}
                <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t">
                  {(dashboardData.heatmap?.time_series_pain_points || []).map((pp) => (
                    <div key={pp.keyword} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">{pp.keyword}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-600">{pp.total_mentions} mentions</span>
                        <div className={`flex items-center text-xs ${
                          pp.growth_rate >= 0 ? 'text-red-600' : 'text-green-600'
                        }`}>
                          {pp.growth_rate >= 0 ? (
                            <TrendingUp className="h-3 w-3 mr-1" />
                          ) : (
                            <TrendingDown className="h-3 w-3 mr-1" />
                          )}
                          {pp.growth_rate >= 0 ? '+' : ''}{pp.growth_rate}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-center text-gray-500 py-8">
                <p className="text-sm">No time series data available</p>
                <p className="text-xs mt-1">Run a campaign to collect historical data</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Community Watchlist */}
      <Card>
        <CardHeader>
          <CardTitle>COMMUNITY WATCHLIST</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-xs font-medium text-gray-600">
                  <th className="text-left py-2 px-2">Rank</th>
                  <th className="text-left py-2 px-2">Community</th>
                  <th className="text-left py-2 px-2">Platform</th>
                  <th className="text-right py-2 px-2">Members</th>
                  <th className="text-right py-2 px-2">Echo</th>
                  <th className="text-right py-2 px-2">Δ</th>
                  <th className="text-right py-2 px-2">Activity</th>
                  <th className="text-right py-2 px-2">4wk Threads</th>
                  <th className="text-right py-2 px-2">Engagement</th>
                  <th className="text-left py-2 px-2">Key Influencer</th>
                </tr>
              </thead>
              <tbody>
                {(dashboardData.community_watchlist || []).map((community, index) => (
                  <tr
                    key={index}
                    className="border-b hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => setSelectedCommunity(community)}
                  >
                    <td className="py-3 px-2 font-medium">{community.rank}</td>
                    <td className="py-3 px-2 font-medium text-gray-900">{community.name}</td>
                    <td className="py-3 px-2">
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        {community.platform.charAt(0).toUpperCase() + community.platform.slice(1)}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-right text-gray-700">
                      {community.member_count >= 1000000
                        ? `${(community.member_count / 1000000).toFixed(1)}M`
                        : community.member_count >= 1000
                        ? `${(community.member_count / 1000).toFixed(1)}k`
                        : community.member_count}
                    </td>
                    <td className="py-3 px-2 text-right font-medium text-gray-900">
                      {community.echo_score.toFixed(1)}
                    </td>
                    <td className="py-3 px-2 text-right">
                      <div className={`flex items-center justify-end ${
                        community.echo_change >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {community.echo_change >= 0 ? (
                          <TrendingUp className="h-3 w-3 mr-1" />
                        ) : (
                          <TrendingDown className="h-3 w-3 mr-1" />
                        )}
                        <span className="font-medium">
                          {community.echo_change >= 0 ? '+' : ''}{community.echo_change.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-2 text-right">
                      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                        community.activity_score >= 7 ? 'bg-green-100 text-green-800' :
                        community.activity_score >= 4 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {community.activity_score.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-right text-gray-700">
                      {community.threads_last_4_weeks}
                    </td>
                    <td className="py-3 px-2 text-right text-gray-700">
                      {community.avg_engagement_rate.toFixed(1)}%
                    </td>
                    <td className="py-3 px-2 text-gray-900 truncate max-w-[120px]">
                      {community.key_influencer}
                    </td>
                  </tr>
                ))}
                {(!dashboardData.community_watchlist || dashboardData.community_watchlist.length === 0) && (
                  <tr>
                    <td colSpan={10} className="py-8 text-center text-gray-500">
                      <p className="text-sm">No communities in watchlist</p>
                      <p className="text-xs mt-1">Run a campaign to discover communities</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Enhanced Analysis Summary */}
      {selectedBrand && analysisSummary && !summaryLoading && (
        <div className="space-y-6">
          {/* Key Insights Section */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-yellow-500" />
                <CardTitle>AI-Powered Key Insights</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysisSummary.key_insights?.slice(0, 6).map((insight: string, index: number) => (
                  <div key={index} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold">
                      {index + 1}
                    </div>
                    <p className="text-sm text-gray-700">{insight}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

        </div>
      )}

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

            {/* Campaign Insights Section */}
            {dashboardData?.campaign_analytics?.insights && dashboardData.campaign_analytics.insights.length > 0 && (
              <div className="mt-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                  <Lightbulb className="h-5 w-5 mr-2 text-yellow-600" />
                  Campaign Insights
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {dashboardData.campaign_analytics.insights.map((insight: any, index: number) => (
                    <div
                      key={index}
                      className={`p-4 rounded-lg border-l-4 ${
                        insight.priority === 'high' ? 'bg-red-50 border-red-500' :
                        insight.priority === 'medium' ? 'bg-yellow-50 border-yellow-500' :
                        'bg-blue-50 border-blue-500'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-medium text-gray-900 text-sm">{insight.category}</h4>
                        <span className={`px-2 py-1 text-xs font-medium rounded ${
                          insight.priority === 'high' ? 'bg-red-100 text-red-800' :
                          insight.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {insight.priority}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 mb-3">{insight.insight}</p>
                      {insight.action_items && insight.action_items.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-gray-600 mb-1">Recommended Actions:</p>
                          <ul className="list-disc list-inside space-y-1">
                            {insight.action_items.map((action: string, idx: number) => (
                              <li key={idx} className="text-xs text-gray-600">{action}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {dashboardData?.campaign_analytics?.data_summary && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600">
                      Insights generated from {dashboardData.campaign_analytics.data_summary.communities} communities, {' '}
                      {dashboardData.campaign_analytics.data_summary.threads} threads, and {' '}
                      {dashboardData.campaign_analytics.data_summary.pain_points} pain points.
                      Overall sentiment: <span className="font-medium">{dashboardData.campaign_analytics.data_summary.sentiment_label}</span>
                    </p>
                  </div>
                )}
              </div>
            )}
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

      {/* Community Detail Modal */}
      {selectedCommunity && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full my-8 max-h-[calc(100vh-4rem)] overflow-hidden flex flex-col">
            <div className="flex-shrink-0 bg-white border-b px-6 py-4 flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{selectedCommunity.name}</h2>
                <div className="flex items-center gap-3 mt-2">
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    {selectedCommunity.platform.charAt(0).toUpperCase() + selectedCommunity.platform.slice(1)}
                  </span>
                  <span className="text-sm text-gray-600">
                    {selectedCommunity.member_count >= 1000000
                      ? `${(selectedCommunity.member_count / 1000000).toFixed(1)}M members`
                      : selectedCommunity.member_count >= 1000
                      ? `${(selectedCommunity.member_count / 1000).toFixed(1)}k members`
                      : `${selectedCommunity.member_count} members`}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedCommunity(null)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="h-6 w-6" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Key Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-xs text-gray-600 mb-1">Echo Score</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {selectedCommunity.echo_score.toFixed(1)}
                  </div>
                  <div className={`flex items-center text-sm mt-1 ${
                    selectedCommunity.echo_change >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {selectedCommunity.echo_change >= 0 ? (
                      <TrendingUp className="h-3 w-3 mr-1" />
                    ) : (
                      <TrendingDown className="h-3 w-3 mr-1" />
                    )}
                    {selectedCommunity.echo_change >= 0 ? '+' : ''}{selectedCommunity.echo_change.toFixed(1)}%
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-xs text-gray-600 mb-1">Activity Score</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {selectedCommunity.activity_score.toFixed(1)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {selectedCommunity.activity_score >= 7 ? 'Very Active' :
                     selectedCommunity.activity_score >= 4 ? 'Moderately Active' : 'Low Activity'}
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-xs text-gray-600 mb-1">4-Week Threads</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {selectedCommunity.threads_last_4_weeks}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Last 7 days: {selectedCommunity.new_threads}</div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="text-xs text-gray-600 mb-1">Avg Engagement</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {selectedCommunity.avg_engagement_rate.toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-500 mt-1">Per thread</div>
                </div>
              </div>

              {/* Key Influencer */}
              <div className="border rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-600 mb-2">Key Influencer</h3>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                    <span className="text-blue-600 font-bold text-lg">
                      {selectedCommunity.key_influencer.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{selectedCommunity.key_influencer}</div>
                    <div className="text-xs text-gray-500">Top contributor in this community</div>
                  </div>
                </div>
              </div>

              {/* Top Pain Points Section */}
              <div className="border rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-600 mb-3">Top Pain Points</h3>
                <div className="space-y-2">
                  {dashboardData?.heatmap?.community_pain_point_matrix
                    ?.find((c: any) => c.community_name === selectedCommunity.name)
                    ?.pain_points?.slice(0, 5)
                    .map((pp: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded">
                        <span className="font-medium text-gray-900">{pp.keyword}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-sm text-gray-600">{pp.mention_count} mentions</span>
                          <span className="text-sm text-green-600 font-medium">+{pp.growth_percentage.toFixed(0)}%</span>
                        </div>
                      </div>
                    )) || (
                    <p className="text-sm text-gray-500 text-center py-4">No pain points data available</p>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={() => fetchCommunityThreads(selectedCommunity.name)}
                  disabled={threadsLoading}
                  className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {threadsLoading ? 'Loading...' : 'View All Threads'}
                </button>
                <button
                  onClick={() => fetchCommunityInfluencers(selectedCommunity.name)}
                  disabled={influencersLoading}
                  className="flex-1 bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {influencersLoading ? 'Loading...' : 'View Influencers'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Threads Modal */}
      {showThreadsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-2xl font-bold text-gray-900">
                Threads from {selectedCommunity?.name}
              </h2>
              <button
                onClick={() => setShowThreadsModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
              {threadsLoading ? (
                <div className="flex justify-center items-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
              ) : communityThreads.length === 0 ? (
                <p className="text-center text-gray-500 py-12">No threads found for this community</p>
              ) : (
                <div className="space-y-4">
                  {communityThreads.map((thread: any, idx: number) => (
                    <div key={idx} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-semibold text-gray-900 flex-1">{thread.title}</h3>
                        <span className="text-xs text-gray-500 ml-4">
                          {new Date(thread.published_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-3 line-clamp-2">{thread.content}</p>
                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        <span>By {thread.author}</span>
                        <span>•</span>
                        <span>Echo: {thread.echo_score?.toFixed(1)}</span>
                        <span>•</span>
                        <span className={thread.sentiment_score >= 0 ? 'text-green-600' : 'text-red-600'}>
                          Sentiment: {thread.sentiment_score?.toFixed(2)}
                        </span>
                        <span>•</span>
                        <span>{thread.comment_count} comments</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Influencers Modal */}
      {showInfluencersModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-2xl font-bold text-gray-900">
                Influencers in {selectedCommunity?.name}
              </h2>
              <button
                onClick={() => setShowInfluencersModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
              {influencersLoading ? (
                <div className="flex justify-center items-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
              ) : communityInfluencers.length === 0 ? (
                <p className="text-center text-gray-500 py-12">No influencers found for this community</p>
              ) : (
                <div className="space-y-4">
                  {communityInfluencers.map((influencer: any, idx: number) => (
                    <div key={idx} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                          {influencer.display_name?.charAt(0).toUpperCase() || 'U'}
                        </div>
                        <div className="flex-1">
                          <div className="flex justify-between items-start mb-2">
                            <div>
                              <h3 className="font-semibold text-gray-900">{influencer.display_name}</h3>
                              <p className="text-sm text-gray-500">@{influencer.username}</p>
                            </div>
                            <span className="text-lg font-bold text-blue-600">
                              {influencer.influence_score?.toFixed(1)}
                            </span>
                          </div>
                          <div className="grid grid-cols-4 gap-3 mt-3">
                            <div>
                              <div className="text-xs text-gray-500">Posts</div>
                              <div className="text-sm font-semibold text-gray-900">{influencer.total_posts}</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-500">Reach</div>
                              <div className="text-sm font-semibold text-gray-900">{influencer.reach_score?.toFixed(0)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-500">Authority</div>
                              <div className="text-sm font-semibold text-gray-900">{influencer.authority_score?.toFixed(0)}</div>
                            </div>
                            <div>
                              <div className="text-xs text-gray-500">Brand Mentions</div>
                              <div className="text-sm font-semibold text-gray-900">{influencer.brand_mention_count}</div>
                            </div>
                          </div>
                          <div className="mt-2 flex items-center gap-2">
                            <span className={`text-xs px-2 py-1 rounded ${
                              influencer.sentiment_towards_brand >= 0.2 ? 'bg-green-100 text-green-800' :
                              influencer.sentiment_towards_brand <= -0.2 ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              Sentiment: {influencer.sentiment_towards_brand?.toFixed(2)}
                            </span>
                            <span className="text-xs text-gray-500">
                              {influencer.brand_mention_rate?.toFixed(1)}% brand mention rate
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
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
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/api/v1/threads/${threadId}/`);
      
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
