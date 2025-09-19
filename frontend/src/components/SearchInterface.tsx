'use client';

import { useState } from 'react';
import { apiService, SearchResult, SearchResponse } from '@/lib/api';
import { formatDate, getSentimentColor, getSentimentLabel } from '@/lib/utils';
import { Search, Filter, Calendar, ThumbsUp, ThumbsDown, Minus } from 'lucide-react';

export default function SearchInterface() {
  const [query, setQuery] = useState('');
  const [contentType, setContentType] = useState<'all' | 'processed' | 'insights'>('all');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiService.searchContent(query, contentType, 20);
      setResults(response.results);
      setSearchResponse(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults([]);
      setSearchResponse(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const getSentimentIcon = (score?: number) => {
    if (score === undefined || score === null) return <Minus className="h-4 w-4 text-gray-400" />;
    if (score > 0.1) return <ThumbsUp className="h-4 w-4 text-green-600" />;
    if (score < -0.1) return <ThumbsDown className="h-4 w-4 text-red-600" />;
    return <Minus className="h-4 w-4 text-gray-400" />;
  };

  return (
    <div className="space-y-6">
      {/* Search Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Content Search</h3>

        {/* Search Input */}
        <div className="flex space-x-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Search content and insights..."
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md text-sm placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Content Type Filter */}
          <div className="flex-shrink-0">
            <select
              value={contentType}
              onChange={(e) => setContentType(e.target.value as 'all' | 'processed' | 'insights')}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Content</option>
              <option value="processed">Processed Content</option>
              <option value="insights">Insights</option>
            </select>
          </div>

          {/* Search Button */}
          <button
            onClick={handleSearch}
            disabled={!query.trim() || isLoading}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Search className="h-4 w-4 mr-2" />
            Search
          </button>
        </div>

        {/* Search Results Summary */}
        {searchResponse && (
          <div className="mt-4 text-sm text-gray-600">
            Found {searchResponse.total_found} results for "{searchResponse.query}"
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}
      </div>

      {/* Search Results */}
      {isLoading ? (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Searching...</span>
          </div>
        </div>
      ) : results.length > 0 ? (
        <div className="space-y-4">
          {results.map((result) => (
            <div key={`${result.type}-${result.id}`} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  {/* Content Type Badge */}
                  <div className="flex items-center space-x-2 mb-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      result.type === 'insight'
                        ? 'bg-purple-100 text-purple-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      {result.type === 'insight' ? 'Insight' : 'Content'}
                    </span>

                    {result.sentiment !== undefined && (
                      <div className="flex items-center space-x-1">
                        {getSentimentIcon(result.sentiment)}
                        <span className={`text-xs ${getSentimentColor(result.sentiment)}`}>
                          {getSentimentLabel(result.sentiment)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Title */}
                  <h4 className="text-lg font-medium text-gray-900 mb-2">
                    {result.title || 'Untitled'}
                  </h4>

                  {/* Content Preview */}
                  <p className="text-gray-600 text-sm mb-3 line-clamp-3">
                    {result.content}
                  </p>

                  {/* Metadata */}
                  <div className="flex items-center space-x-4 text-xs text-gray-500">
                    {result.campaign && (
                      <span className="flex items-center">
                        <Filter className="h-3 w-3 mr-1" />
                        {result.campaign}
                      </span>
                    )}
                    {result.source && (
                      <span>Source: {result.source}</span>
                    )}
                    {result.published_at && (
                      <span className="flex items-center">
                        <Calendar className="h-3 w-3 mr-1" />
                        {formatDate(result.published_at)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : searchResponse && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-center text-gray-500">
            <Search className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No results found for your search.</p>
            <p className="text-sm mt-2">Try different keywords or check your filters.</p>
          </div>
        </div>
      )}

      {/* Example Searches */}
      {!searchResponse && !isLoading && (
        <div className="bg-white rounded-lg shadow p-6">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Example Searches</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              'product feedback',
              'user experience',
              'customer satisfaction',
              'feature requests'
            ].map((example) => (
              <button
                key={example}
                onClick={() => {
                  setQuery(example);
                  handleSearch();
                }}
                className="text-left px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-md border border-blue-200 hover:border-blue-300"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}