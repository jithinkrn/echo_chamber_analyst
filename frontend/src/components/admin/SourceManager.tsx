'use client';

import { useState, useEffect } from 'react';
import { Sparkles, Globe, TrendingUp, Brain, ExternalLink, RefreshCw } from 'lucide-react';
import { apiService } from '../../lib/api';

interface DiscoveredSource {
  brand_name: string;
  focus: string;
  industry: string;
  reddit_communities: string[];
  forums: string[];
  reasoning: string;
  discovered_at: string;
  cache_hit?: boolean;
  is_fallback?: boolean;
}

interface Campaign {
  id: string;
  name: string;
  brand?: {
    name: string;
  };
}

export default function SourceManager() {
  const [discoveredSources, setDiscoveredSources] = useState<DiscoveredSource[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedBrand, setSelectedBrand] = useState<string>('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);

      // Fetch campaigns to get brands
      const campaignsResponse = await apiService.getCampaigns();
      const campaignsList = campaignsResponse.campaigns || [];
      setCampaigns(campaignsList);

      // Try to fetch LLM-discovered sources from the backend
      // This will require a new API endpoint
      await fetchDiscoveredSources();

    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDiscoveredSources = async () => {
    try {
      // Call new API endpoint to get LLM-discovered sources
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/v1/discovered-sources/`);
      if (response.ok) {
        const data = await response.json();
        setDiscoveredSources(data.sources || []);
      }
    } catch (error) {
      console.error('Failed to fetch discovered sources:', error);
      // If the endpoint doesn't exist yet, we'll show empty state
      setDiscoveredSources([]);
    }
  };

  const refreshDiscovery = async (brandName: string) => {
    try {
      setLoading(true);
      // Trigger a fresh LLM discovery by clearing cache
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/v1/discover-sources/?brand=${brandName}&refresh=true&industry=general&focus=comprehensive`);
      if (response.ok) {
        const data = await response.json();
        // Update the discovered sources list
        setDiscoveredSources(prev => {
          const filtered = prev.filter(s => s.brand_name !== brandName);
          return [...filtered, data];
        });
      }
    } catch (error) {
      console.error('Failed to refresh discovery:', error);
    } finally {
      setLoading(false);
    }
  };

  // Get unique brands from campaigns
  const uniqueBrands = Array.from(
    new Set(campaigns.map(c => c.brand?.name).filter(Boolean))
  );

  const filteredSources = selectedBrand
    ? discoveredSources.filter(s => s.brand_name === selectedBrand)
    : discoveredSources;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
        <span className="ml-2 text-gray-600">Loading LLM-discovered sources...</span>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center space-x-3">
            <Brain className="h-8 w-8 text-purple-600" />
            <h2 className="text-2xl font-bold text-gray-900">AI-Discovered Sources</h2>
          </div>
          <p className="text-gray-600 mt-2">
            Intelligent source recommendations powered by GPT-4 based on brand context and industry
          </p>
        </div>

        {/* Brand Filter */}
        {uniqueBrands.length > 0 && (
          <div className="flex items-center space-x-2">
            <label className="text-sm text-gray-600">Filter by brand:</label>
            <select
              value={selectedBrand}
              onChange={(e) => setSelectedBrand(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">All Brands</option>
              {uniqueBrands.map(brand => (
                <option key={brand} value={brand}>{brand}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <Sparkles className="h-5 w-5 text-purple-600" />
            <div className="text-purple-600 text-sm font-medium">Brands Analyzed</div>
          </div>
          <div className="text-2xl font-bold text-purple-900 mt-1">{uniqueBrands.length}</div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <Globe className="h-5 w-5 text-blue-600" />
            <div className="text-blue-600 text-sm font-medium">Reddit Communities</div>
          </div>
          <div className="text-2xl font-bold text-blue-900 mt-1">
            {discoveredSources.reduce((acc, s) => acc + s.reddit_communities.length, 0)}
          </div>
        </div>

        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5 text-green-600" />
            <div className="text-green-600 text-sm font-medium">Forums Discovered</div>
          </div>
          <div className="text-2xl font-bold text-green-900 mt-1">
            {discoveredSources.reduce((acc, s) => acc + s.forums.length, 0)}
          </div>
        </div>

        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <Brain className="h-5 w-5 text-orange-600" />
            <div className="text-orange-600 text-sm font-medium">LLM Discoveries</div>
          </div>
          <div className="text-2xl font-bold text-orange-900 mt-1">{discoveredSources.length}</div>
        </div>
      </div>

      {/* Discovered Sources */}
      {filteredSources.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <Brain className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">No Sources Discovered Yet</h3>
          <p className="text-gray-600 mb-4 max-w-md mx-auto">
            LLM-powered source discovery happens automatically when campaigns run.
            Create and run a campaign to see AI-recommended sources appear here.
          </p>
          <div className="text-sm text-gray-500">
            The system uses GPT-4 to intelligently recommend the best Reddit communities and forums
            based on your brand, industry, and analysis focus.
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {filteredSources.map((source, idx) => (
            <div key={idx} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              {/* Header */}
              <div className="px-6 py-4 bg-gradient-to-r from-purple-50 to-blue-50 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Sparkles className="h-6 w-6 text-purple-600" />
                    <div>
                      <h3 className="text-lg font-bold text-gray-900">{source.brand_name}</h3>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                          {source.industry}
                        </span>
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                          Focus: {source.focus}
                        </span>
                        {source.cache_hit && (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                            Cached
                          </span>
                        )}
                        {source.is_fallback && (
                          <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded">
                            Fallback
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => refreshDiscovery(source.brand_name)}
                    className="flex items-center space-x-2 px-3 py-1.5 bg-white border border-purple-200 text-purple-600 rounded-md hover:bg-purple-50 transition text-sm"
                  >
                    <RefreshCw className="h-4 w-4" />
                    <span>Refresh</span>
                  </button>
                </div>
              </div>

              {/* LLM Reasoning */}
              <div className="px-6 py-4 bg-blue-50 border-b border-gray-200">
                <div className="flex items-start space-x-2">
                  <Brain className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <h4 className="text-sm font-semibold text-blue-900 mb-1">AI Reasoning</h4>
                    <p className="text-sm text-blue-800">{source.reasoning}</p>
                  </div>
                </div>
              </div>

              {/* Sources Content */}
              <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Reddit Communities */}
                <div>
                  <h4 className="text-md font-semibold text-gray-900 mb-3 flex items-center space-x-2">
                    <Globe className="h-5 w-5 text-blue-600" />
                    <span>Reddit Communities ({source.reddit_communities.length})</span>
                  </h4>
                  <div className="space-y-2">
                    {source.reddit_communities.map((community, i) => (
                      <a
                        key={i}
                        href={`https://reddit.com/r/${community}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition group"
                      >
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                          <span className="font-medium text-gray-900">r/{community}</span>
                        </div>
                        <ExternalLink className="h-4 w-4 text-gray-400 group-hover:text-blue-600" />
                      </a>
                    ))}
                  </div>
                </div>

                {/* Forums */}
                <div>
                  <h4 className="text-md font-semibold text-gray-900 mb-3 flex items-center space-x-2">
                    <TrendingUp className="h-5 w-5 text-green-600" />
                    <span>Forums & Websites ({source.forums.length})</span>
                  </h4>
                  <div className="space-y-2">
                    {source.forums.map((forum, i) => (
                      <a
                        key={i}
                        href={`https://${forum}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:border-green-300 hover:bg-green-50 transition group"
                      >
                        <div className="flex items-center space-x-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <span className="font-medium text-gray-900">{forum}</span>
                        </div>
                        <ExternalLink className="h-4 w-4 text-gray-400 group-hover:text-green-600" />
                      </a>
                    ))}
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
                <p className="text-xs text-gray-500">
                  Discovered on {new Date(source.discovered_at).toLocaleString()}
                  {source.cache_hit ? ' (from cache)' : ' (fresh discovery)'}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
