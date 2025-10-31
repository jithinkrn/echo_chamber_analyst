'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Users, MessageSquare, AlertTriangle, Building, ChevronDown, Lightbulb, Target } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter, ZAxis, Cell } from 'recharts';
import InfluencerPulse from './InfluencerPulse';
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
  };
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
  const [analysisSummary, setAnalysisSummary] = useState<any>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

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
                const chartHeight = Math.max(250, painPoints.length * 50);
                const barColors = [
                  '#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6',
                  '#8b5cf6', '#ec4899', '#06b6d4', '#f43f5e', '#84cc16',
                ];
                return (
                  <ResponsiveContainer width="100%" height={chartHeight}>
                    <BarChart data={painPoints} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis type="number" stroke="#6b7280" style={{ fontSize: '11px' }}
                        label={{ value: 'Growth %', position: 'insideBottom', offset: -5, style: { fontSize: '11px' } }} />
                      <YAxis type="category" dataKey="keyword" stroke="#6b7280" style={{ fontSize: '11px' }} width={90} />
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
                        label={{ position: 'right', formatter: (value: number) => `+${value.toFixed(0)}%`,
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
                  <div className="space-y-4">
                    <ResponsiveContainer width="100%" height={400}>
                      <ScatterChart margin={{ top: 20, right: 20, bottom: 80, left: 100 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis type="category" dataKey="community" name="Community" allowDuplicatedCategory={false}
                          stroke="#6b7280" angle={-45} textAnchor="end" height={80} interval={0} style={{ fontSize: '11px' }} />
                        <YAxis type="category" dataKey="painPoint" name="Pain Point" allowDuplicatedCategory={false}
                          stroke="#6b7280" style={{ fontSize: '11px' }} width={90} />
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
                        <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
                          content={() => (
                            <div className="flex flex-wrap justify-center gap-3 mt-4">
                              {painPointsList.map((pp, idx) => (
                                <div key={idx} className="flex items-center gap-2">
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
                          week: weekData.week,
                          dateRange: weekData.date_range,
                          Total: totalSeries[idx]?.mention_count || 0
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
                        const dataPoint = (dashboardData.heatmap?.time_series_pain_points?.[0]?.time_series || []).find((d: any) => d.week === label);
                        return dataPoint ? `${label} (${dataPoint.date_range})` : label;
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

          {/* Pain Points Analysis with Influencer Impact */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-500" />
                <CardTitle>Urgent Pain Points with Influencer Reach</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-6 gap-2 text-xs font-medium text-gray-600 border-b pb-2">
                  <span className="col-span-2">Pain Point</span>
                  <span>Urgency</span>
                  <span>Sentiment</span>
                  <span>Influencers</span>
                  <span>Est. Reach</span>
                </div>
                {analysisSummary.pain_point_analysis?.urgent_pain_points?.slice(0, 5).map((pp: any, index: number) => (
                  <div key={index} className="grid grid-cols-6 gap-2 text-sm items-center">
                    <span className="col-span-2 font-medium text-gray-900">{pp.pain_point}</span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      pp.urgency_score >= 7 ? 'bg-red-100 text-red-800' :
                      pp.urgency_score >= 5 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {pp.urgency_score}/10
                    </span>
                    <span className={`text-xs ${
                      pp.sentiment_breakdown.positive > pp.sentiment_breakdown.negative
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}>
                      {pp.sentiment_breakdown.positive > pp.sentiment_breakdown.negative ? '😊' : '😞'}
                      {' '}{pp.sentiment_breakdown.positive}/{pp.sentiment_breakdown.negative}
                    </span>
                    <span className="text-gray-700">{pp.influencer_count}</span>
                    <span className="font-medium text-blue-600">
                      {pp.estimated_reach >= 1000
                        ? `${(pp.estimated_reach / 1000).toFixed(1)}k`
                        : pp.estimated_reach}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Influencer Breakdown */}
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">
                  High Influence Users
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-blue-600">
                  {analysisSummary.influencer_breakdown?.high_influence_count || 0}
                </div>
                <p className="text-xs text-gray-500 mt-1">Score &gt; 70</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">
                  Brand Advocates
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-green-600">
                  {analysisSummary.influencer_breakdown?.advocates || 0}
                </div>
                <p className="text-xs text-gray-500 mt-1">Positive sentiment</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">
                  Critics
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-red-600">
                  {analysisSummary.influencer_breakdown?.critics || 0}
                </div>
                <p className="text-xs text-gray-500 mt-1">Negative sentiment</p>
              </CardContent>
            </Card>
          </div>

          {/* Community Insights */}
          {analysisSummary.community_insights?.top_communities && (
            <Card>
              <CardHeader>
                <CardTitle>Top Communities by Engagement</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {analysisSummary.community_insights.top_communities.slice(0, 4).map((community: any, index: number) => (
                    <div key={index} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex justify-between items-start mb-2">
                        <span className="font-medium text-gray-900">{community.name}</span>
                        <span className="text-xs text-gray-500">{community.platform}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                        <div>Threads: <span className="font-medium">{community.thread_count}</span></div>
                        <div>Avg Sentiment: <span className="font-medium">{community.avg_sentiment?.toFixed(2)}</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Influencer Pulse - Full Width Component */}
      {selectedBrand && (
        <InfluencerPulse brandId={selectedBrand} />
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
            {analysisSummary?.insights && analysisSummary.insights.length > 0 && (
              <div className="mt-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
                  <Lightbulb className="h-5 w-5 mr-2 text-yellow-600" />
                  Campaign Insights
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {analysisSummary.insights.map((insight: any, index: number) => (
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

                {analysisSummary?.data_summary && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-600">
                      Insights generated from {analysisSummary.data_summary.communities} communities, {' '}
                      {analysisSummary.data_summary.threads} threads, and {' '}
                      {analysisSummary.data_summary.pain_points} pain points.
                      Overall sentiment: <span className="font-medium">{analysisSummary.data_summary.sentiment_label}</span>
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

      {/* High-Echo Communities Modal */}
      {showCommunitiesModal && dashboardData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowCommunitiesModal(false)}>
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">High-Echo Communities</h2>
              <button onClick={() => setShowCommunitiesModal(false)} className="text-gray-500 hover:text-gray-700">
                ✕
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Communities with echo chamber score ≥ 7.0
            </p>
            <div className="space-y-3">
              {(dashboardData.community_watchlist || []).map((community, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-medium text-gray-900">#{community.rank} {community.name}</h3>
                      <p className="text-sm text-gray-600 mt-1">Key Influencer: {community.key_influencer}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-gray-900">{community.echo_score.toFixed(1)}</div>
                      <div className={`text-xs ${community.echo_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {community.echo_change >= 0 ? '+' : ''}{community.echo_change.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 text-sm text-gray-700">
                    {community.new_threads} new threads this week
                  </div>
                </div>
              ))}
              {(!dashboardData.community_watchlist || dashboardData.community_watchlist.length === 0) && (
                <p className="text-center text-gray-500 py-8">No high-echo communities found</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Pain Points Modal */}
      {showPainPointsModal && dashboardData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowPainPointsModal(false)}>
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">High-Growth Pain Points</h2>
              <button onClick={() => setShowPainPointsModal(false)} className="text-gray-500 hover:text-gray-700">
                ✕
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Pain points with growth &gt; 50% in the last week
            </p>
            <div className="space-y-3">
              {(dashboardData.top_pain_points || []).map((painPoint, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900">{painPoint.keyword}</h3>
                      <p className="text-sm text-gray-600 mt-1">{painPoint.mention_count} mentions</p>
                    </div>
                    <div className="text-right">
                      <div className={`text-lg font-bold ${
                        painPoint.growth_percentage >= 100 ? 'text-red-600' :
                        painPoint.growth_percentage >= 50 ? 'text-orange-600' :
                        'text-yellow-600'
                      }`}>
                        +{painPoint.growth_percentage.toFixed(0)}%
                      </div>
                      <div className="text-xs text-gray-500">growth</div>
                    </div>
                  </div>
                </div>
              ))}
              {(!dashboardData.top_pain_points || dashboardData.top_pain_points.length === 0) && (
                <p className="text-center text-gray-500 py-8">No high-growth pain points found</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Sentiment Analysis Modal */}
      {showSentimentModal && dashboardData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowSentimentModal(false)}>
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">Sentiment Analysis</h2>
              <button onClick={() => setShowSentimentModal(false)} className="text-gray-500 hover:text-gray-700">
                ✕
              </button>
            </div>
            <div className="space-y-6">
              <div>
                <h3 className="font-medium text-gray-900 mb-3">Overall Positivity</h3>
                <div className="bg-gray-100 rounded-lg p-4">
                  <div className="text-4xl font-bold text-gray-900 mb-2">
                    {dashboardData.kpis.positivity_ratio}% 😊
                  </div>
                  <div className="flex items-center text-sm">
                    <TrendingDown className="h-4 w-4 mr-1 text-red-600" />
                    <span className="text-red-600">{dashboardData.kpis.positivity_change_pp} percentage points from yesterday</span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-medium text-gray-900 mb-3">Sentiment Breakdown</h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded">
                    <span className="text-sm font-medium text-green-900">Positive Sentiment</span>
                    <span className="text-sm font-bold text-green-900">
                      {Math.max(0, dashboardData.kpis.positivity_ratio).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <span className="text-sm font-medium text-gray-900">Neutral Sentiment</span>
                    <span className="text-sm font-bold text-gray-900">
                      {Math.min(100, Math.max(0, 100 - dashboardData.kpis.positivity_ratio - (100 - dashboardData.kpis.positivity_ratio))).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-red-50 rounded">
                    <span className="text-sm font-medium text-red-900">Negative Sentiment</span>
                    <span className="text-sm font-bold text-red-900">
                      {Math.max(0, 100 - dashboardData.kpis.positivity_ratio).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-medium text-gray-900 mb-3">Recommendations</h3>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <ul className="list-disc list-inside space-y-2 text-sm text-blue-900">
                    {dashboardData.kpis.positivity_ratio < 50 ? (
                      <>
                        <li>Address negative sentiment through targeted community engagement</li>
                        <li>Monitor pain points and respond to customer concerns</li>
                        <li>Highlight positive customer experiences and success stories</li>
                      </>
                    ) : (
                      <>
                        <li>Maintain positive momentum through consistent engagement</li>
                        <li>Leverage positive sentiment for marketing campaigns</li>
                        <li>Continue monitoring for emerging pain points</li>
                      </>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
