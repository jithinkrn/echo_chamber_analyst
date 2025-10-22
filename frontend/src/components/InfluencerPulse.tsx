import { useState, useEffect } from 'react';
import { Users, TrendingUp, MessageCircle, Award, ExternalLink, Activity } from 'lucide-react';
import { apiService } from '../lib/api';

interface Influencer {
  id: string;
  username: string;
  display_name: string;
  platform: string;
  profile_url: string;

  // Influence scores
  reach_score: number;
  authority_score: number;
  advocacy_score: number;
  relevance_score: number;
  influence_score: number;

  // Engagement metrics
  total_posts: number;
  total_karma: number;
  avg_post_score: number;
  total_comments: number;
  avg_engagement_rate: number;

  // Brand sentiment
  sentiment: number;
  brand_mention_count: number;
  brand_mention_rate: number;

  // Activity
  communities: string[];
  post_frequency: number;
  last_active: string | null;

  // Community
  community?: {
    id: string;
    name: string;
    platform: string;
  };
}

interface InfluencerPulseProps {
  brandId: string;
}

export default function InfluencerPulse({ brandId }: InfluencerPulseProps) {
  const [influencers, setInfluencers] = useState<Influencer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [minScore, setMinScore] = useState(0);

  useEffect(() => {
    if (brandId) {
      fetchInfluencers();
    }
  }, [brandId, minScore]);

  const fetchInfluencers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.getBrandInfluencers(brandId, {
        limit: 20,
        min_score: minScore
      });
      setInfluencers(response.influencers || []);
    } catch (err: any) {
      console.error('Failed to fetch influencers:', err);
      setError(err.response?.data?.error || 'Failed to load influencers');
    } finally {
      setLoading(false);
    }
  };

  const getSentimentIcon = (sentiment: number) => {
    if (sentiment > 0.3) return '=M';
    if (sentiment < -0.3) return '=N';
    return '=';
  };

  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0.3) return 'text-green-600 bg-green-50';
    if (sentiment < -0.3) return 'text-red-600 bg-red-50';
    return 'text-yellow-600 bg-yellow-50';
  };

  const getInfluenceLevel = (score: number) => {
    if (score >= 75) return { label: 'High', color: 'text-purple-700 bg-purple-100' };
    if (score >= 50) return { label: 'Medium', color: 'text-blue-700 bg-blue-100' };
    return { label: 'Low', color: 'text-gray-700 bg-gray-100' };
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays} days ago`;
      if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
      return `${Math.floor(diffDays / 30)} months ago`;
    } catch {
      return 'Unknown';
    }
  };

  if (loading && influencers.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-2 mb-6">
          <Users className="h-6 w-6 text-purple-600 animate-pulse" />
          <h2 className="text-xl font-bold text-gray-900">Influencer Pulse</h2>
        </div>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Users className="h-6 w-6 text-purple-600" />
          <h2 className="text-xl font-bold text-gray-900">Influencer Pulse</h2>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (influencers.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Users className="h-6 w-6 text-purple-600" />
          <h2 className="text-xl font-bold text-gray-900">Influencer Pulse</h2>
        </div>
        <div className="text-center py-12">
          <Users className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Influencers Found</h3>
          <p className="text-gray-600 mb-4">
            Start brand analysis to identify influential users in your target communities.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Users className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Influencer Pulse</h2>
              <p className="text-sm text-gray-600">Key voices in your brand communities</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">
              <span className="font-semibold text-purple-600">{influencers.length}</span> influencers tracked
            </span>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center space-x-4">
          <label className="text-sm text-gray-700">Min Influence Score:</label>
          <select
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="0">All (0+)</option>
            <option value="25">Low (25+)</option>
            <option value="50">Medium (50+)</option>
            <option value="75">High (75+)</option>
          </select>
        </div>
      </div>

      {/* Influencer List */}
      <div className="p-6 space-y-4 max-h-[800px] overflow-y-auto">
        {influencers.map((influencer) => {
          const influenceLevel = getInfluenceLevel(influencer.influence_score);

          return (
            <div
              key={influencer.id}
              className="border border-gray-200 rounded-lg p-4 hover:border-purple-300 hover:shadow-md transition-all duration-200"
            >
              {/* Header Row */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-semibold text-gray-900 text-lg">{influencer.display_name}</h3>
                    <span className={`text-xs px-2 py-1 rounded-full ${influenceLevel.color} font-medium`}>
                      {influenceLevel.label}
                    </span>
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                      {influencer.platform}
                    </span>
                  </div>

                  <div className="flex items-center space-x-4 text-sm text-gray-600">
                    <span className="flex items-center">
                      <Activity className="h-3 w-3 mr-1" />
                      Last active: {formatDate(influencer.last_active)}
                    </span>
                    {influencer.profile_url && (
                      <a
                        href={influencer.profile_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center text-purple-600 hover:text-purple-700"
                      >
                        View Profile
                        <ExternalLink className="h-3 w-3 ml-1" />
                      </a>
                    )}
                  </div>
                </div>

                {/* Sentiment Badge */}
                <div className={`px-3 py-2 rounded-lg ${getSentimentColor(influencer.sentiment)} flex items-center space-x-2`}>
                  <span className="text-2xl">{getSentimentIcon(influencer.sentiment)}</span>
                  <div className="text-xs">
                    <div className="font-medium">Sentiment</div>
                    <div>{(influencer.sentiment * 100).toFixed(0)}%</div>
                  </div>
                </div>
              </div>

              {/* Influence Scores Grid */}
              <div className="grid grid-cols-4 gap-3 mb-3 bg-gray-50 p-3 rounded-lg">
                <div>
                  <div className="text-xs text-gray-500 mb-1">Reach</div>
                  <div className="flex items-center space-x-1">
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${influencer.reach_score}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-semibold text-gray-900 w-10 text-right">
                      {influencer.reach_score.toFixed(0)}
                    </span>
                  </div>
                </div>

                <div>
                  <div className="text-xs text-gray-500 mb-1">Authority</div>
                  <div className="flex items-center space-x-1">
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${influencer.authority_score}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-semibold text-gray-900 w-10 text-right">
                      {influencer.authority_score.toFixed(0)}
                    </span>
                  </div>
                </div>

                <div>
                  <div className="text-xs text-gray-500 mb-1">Advocacy</div>
                  <div className="flex items-center space-x-1">
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-purple-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${influencer.advocacy_score}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-semibold text-gray-900 w-10 text-right">
                      {influencer.advocacy_score.toFixed(0)}
                    </span>
                  </div>
                </div>

                <div>
                  <div className="text-xs text-gray-500 mb-1">Relevance</div>
                  <div className="flex items-center space-x-1">
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-yellow-500 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${influencer.relevance_score}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-semibold text-gray-900 w-10 text-right">
                      {influencer.relevance_score.toFixed(0)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Engagement Metrics */}
              <div className="grid grid-cols-5 gap-4 mb-3">
                <div className="text-center">
                  <div className="text-xs text-gray-500 mb-1">Total Posts</div>
                  <div className="text-lg font-bold text-gray-900">{formatNumber(influencer.total_posts)}</div>
                </div>

                <div className="text-center">
                  <div className="text-xs text-gray-500 mb-1">Total Karma</div>
                  <div className="text-lg font-bold text-gray-900">{formatNumber(influencer.total_karma)}</div>
                </div>

                <div className="text-center">
                  <div className="text-xs text-gray-500 mb-1">Avg Score</div>
                  <div className="text-lg font-bold text-gray-900">{influencer.avg_post_score.toFixed(1)}</div>
                </div>

                <div className="text-center">
                  <div className="text-xs text-gray-500 mb-1">Engagement</div>
                  <div className="text-lg font-bold text-gray-900">{(influencer.avg_engagement_rate * 100).toFixed(1)}%</div>
                </div>

                <div className="text-center">
                  <div className="text-xs text-gray-500 mb-1">Brand Mentions</div>
                  <div className="text-lg font-bold text-purple-600">{influencer.brand_mention_count}</div>
                </div>
              </div>

              {/* Communities */}
              <div className="flex items-center space-x-2 text-xs">
                <span className="text-gray-500">Active in:</span>
                <div className="flex flex-wrap gap-1">
                  {influencer.communities.slice(0, 5).map((community, idx) => (
                    <span key={idx} className="bg-blue-50 text-blue-700 px-2 py-1 rounded">
                      {community}
                    </span>
                  ))}
                  {influencer.communities.length > 5 && (
                    <span className="text-gray-500">+{influencer.communities.length - 5} more</span>
                  )}
                </div>
              </div>

              {/* High-value indicator */}
              {influencer.influence_score >= 75 && influencer.sentiment > 0.3 && (
                <div className="mt-3 flex items-center space-x-2 bg-yellow-50 border border-yellow-200 rounded px-3 py-2">
                  <Award className="h-4 w-4 text-yellow-600" />
                  <span className="text-xs text-yellow-800 font-medium">
                    High-Value Advocate - Strong positive sentiment with high influence
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary Footer */}
      <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <div className="flex items-center space-x-6">
            <span>
              <strong className="text-gray-900">{influencers.filter(i => i.sentiment > 0.3).length}</strong> positive advocates
            </span>
            <span>
              <strong className="text-gray-900">{influencers.filter(i => i.influence_score >= 75).length}</strong> high influence
            </span>
            <span>
              Avg Influence: <strong className="text-gray-900">
                {(influencers.reduce((sum, i) => sum + i.influence_score, 0) / influencers.length).toFixed(1)}
              </strong>
            </span>
          </div>
          <button
            onClick={fetchInfluencers}
            className="text-purple-600 hover:text-purple-700 font-medium"
            disabled={loading}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>
    </div>
  );
}
