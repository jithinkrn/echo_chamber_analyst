"use client";

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ArrowLeft, Users, TrendingUp, Award, Heart, Target } from 'lucide-react';

interface Influencer {
  username: string;
  display_name: string;
  platform: string;
  influence_score: number;
  reach_score: number;
  authority_score: number;
  advocacy_score: number;
  relevance_score: number;
  brand_mentions: number;
  sentiment: number;
  reach: number;
  engagement_rate: number;
}

interface Community {
  id: string;
  name: string;
  platform: string;
}

export default function CommunityInfluencersPage() {
  const params = useParams();
  const communityId = params.id as string;
  
  const [influencers, setInfluencers] = useState<Influencer[]>([]);
  const [community, setCommunity] = useState<Community | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInfluencers = async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/v1/community/${communityId}/influencers/`,
          {
            headers: {
              'Content-Type': 'application/json'
            }
          }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch influencers');
        }

        const data = await response.json();
        setInfluencers(data.influencers);
        setCommunity(data.community);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    if (communityId) {
      fetchInfluencers();
    }
  }, [communityId]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-50 border-green-200';
    if (score >= 60) return 'text-blue-600 bg-blue-50 border-blue-200';
    if (score >= 40) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-gray-600 bg-gray-50 border-gray-200';
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.3) return 'text-green-600';
    if (score < -0.3) return 'text-red-600';
    return 'text-gray-600';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading influencers...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">Error: {error}</p>
          <button
            onClick={() => window.close()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Close Window
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => window.close()}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="h-5 w-5 text-gray-600" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {community?.name || 'Community'} Influencers
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                  {influencers.length} influencers · {community?.platform}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Influencers Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {influencers.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">No influencers found for this community</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {influencers.map((influencer, index) => (
              <div
                key={index}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="h-12 w-12 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-lg">
                      {influencer.display_name?.charAt(0) || influencer.username.charAt(0)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {influencer.display_name || influencer.username}
                      </h3>
                      <p className="text-sm text-gray-500">@{influencer.username}</p>
                    </div>
                  </div>
                  <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full capitalize">
                    {influencer.platform}
                  </span>
                </div>

                {/* Overall Influence Score */}
                <div className={`mb-4 p-4 rounded-lg border ${getScoreColor(influencer.influence_score)}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Influence Score</span>
                    <span className="text-2xl font-bold">{influencer.influence_score.toFixed(1)}</span>
                  </div>
                </div>

                {/* Component Scores */}
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-blue-600" />
                    <div>
                      <div className="text-xs text-gray-500">Reach</div>
                      <div className="text-sm font-semibold text-gray-900">
                        {influencer.reach_score.toFixed(0)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Award className="h-4 w-4 text-purple-600" />
                    <div>
                      <div className="text-xs text-gray-500">Authority</div>
                      <div className="text-sm font-semibold text-gray-900">
                        {influencer.authority_score.toFixed(0)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Heart className="h-4 w-4 text-pink-600" />
                    <div>
                      <div className="text-xs text-gray-500">Advocacy</div>
                      <div className="text-sm font-semibold text-gray-900">
                        {influencer.advocacy_score.toFixed(0)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Target className="h-4 w-4 text-orange-600" />
                    <div>
                      <div className="text-xs text-gray-500">Relevance</div>
                      <div className="text-sm font-semibold text-gray-900">
                        {influencer.relevance_score.toFixed(0)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Metrics */}
                <div className="border-t pt-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Reach:</span>
                    <span className="font-medium text-gray-900">
                      {influencer.reach >= 1000000
                        ? `${(influencer.reach / 1000000).toFixed(1)}M`
                        : influencer.reach >= 1000
                        ? `${(influencer.reach / 1000).toFixed(1)}k`
                        : influencer.reach}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Engagement Rate:</span>
                    <span className="font-medium text-gray-900">
                      {influencer.engagement_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Brand Mentions:</span>
                    <span className="font-medium text-gray-900">
                      {influencer.brand_mentions}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Sentiment:</span>
                    <span className={`font-medium ${getSentimentColor(influencer.sentiment)}`}>
                      {influencer.sentiment > 0 ? '+' : ''}{influencer.sentiment.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
