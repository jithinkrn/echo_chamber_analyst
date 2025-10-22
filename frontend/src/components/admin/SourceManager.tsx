'use client';

import { useState, useEffect } from 'react';
import { Plus, Globe, Trash, CheckCircle, Database, ExternalLink } from 'lucide-react';
import { apiService } from '../../lib/api';
import { AddSourceModal } from '../modals/AddSourceModal';

interface Source {
  id: string;
  name: string;
  platform: string;
  url: string;
  description?: string;
  category?: string;
  is_default: boolean;
  is_active?: boolean;
  member_count?: number;
  created_at?: string;
}

export default function SourceManager() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedDefaults, setSelectedDefaults] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchSources();
  }, []);

  const fetchSources = async () => {
    try {
      setLoading(true);
      const response = await apiService.getSources();
      setSources(response.sources || []);
    } catch (error) {
      console.error('Failed to fetch sources:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCustomSource = async (sourceId: string) => {
    if (!confirm('Are you sure you want to delete this custom source?')) return;

    try {
      await apiService.deleteCustomSource(sourceId);
      setSources(sources.filter(s => s.id !== sourceId));
    } catch (error) {
      console.error('Failed to delete source:', error);
      alert('Failed to delete source');
    }
  };

  const toggleDefaultSelection = (sourceId: string) => {
    const newSelected = new Set(selectedDefaults);
    if (newSelected.has(sourceId)) {
      newSelected.delete(sourceId);
    } else {
      newSelected.add(sourceId);
    }
    setSelectedDefaults(newSelected);
  };

  const defaultSources = sources.filter(s => s.is_default);
  const customSources = sources.filter(s => !s.is_default);

  const groupedDefaults = {
    reddit: defaultSources.filter(s => s.platform === 'reddit'),
    forum: defaultSources.filter(s => s.platform === 'forum')
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading sources...</span>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Source Management</h2>
          <p className="text-gray-600 mt-1">Manage default and custom data sources for brand analysis</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
        >
          <Plus className="h-4 w-4" />
          <span>Add Custom Source</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="text-blue-600 text-sm font-medium">Default Sources</div>
          <div className="text-2xl font-bold text-blue-900 mt-1">{defaultSources.length}</div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="text-green-600 text-sm font-medium">Custom Sources</div>
          <div className="text-2xl font-bold text-green-900 mt-1">{customSources.length}</div>
        </div>
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="text-purple-600 text-sm font-medium">Total Sources</div>
          <div className="text-2xl font-bold text-purple-900 mt-1">{sources.length}</div>
        </div>
      </div>

      {/* Default Sources Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center space-x-2">
            <Database className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">Default Sources</h3>
          </div>
          <p className="text-sm text-gray-600 mt-1">
            Pre-configured sources available for all brands. Select defaults when creating a brand.
          </p>
        </div>

        <div className="p-6 space-y-6">
          {/* Reddit Sources */}
          <div>
            <h4 className="text-md font-medium text-gray-700 mb-3 flex items-center space-x-2">
              <Globe className="h-4 w-4" />
              <span>Reddit Communities ({groupedDefaults.reddit.length})</span>
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {groupedDefaults.reddit.map((source) => (
                <div
                  key={source.id}
                  className="border border-gray-200 rounded-lg p-3 hover:border-blue-300 transition cursor-pointer"
                  onClick={() => toggleDefaultSelection(source.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={selectedDefaults.has(source.id)}
                          onChange={() => toggleDefaultSelection(source.id)}
                          className="rounded text-blue-600"
                          onClick={(e) => e.stopPropagation()}
                        />
                        <h5 className="font-medium text-gray-900 text-sm">{source.name}</h5>
                      </div>
                      {source.description && (
                        <p className="text-xs text-gray-600 mt-1 ml-6">{source.description}</p>
                      )}
                      <div className="flex items-center space-x-2 mt-2 ml-6">
                        {source.category && (
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                            {source.category}
                          </span>
                        )}
                        {source.member_count && (
                          <span className="text-xs text-gray-500">
                            {(source.member_count / 1000).toFixed(0)}K members
                          </span>
                        )}
                      </div>
                    </div>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-gray-400 hover:text-blue-600 ml-2"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Forum Sources */}
          {groupedDefaults.forum.length > 0 && (
            <div>
              <h4 className="text-md font-medium text-gray-700 mb-3 flex items-center space-x-2">
                <Globe className="h-4 w-4" />
                <span>Forums & Discussion Boards ({groupedDefaults.forum.length})</span>
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {groupedDefaults.forum.map((source) => (
                  <div
                    key={source.id}
                    className="border border-gray-200 rounded-lg p-3 hover:border-blue-300 transition cursor-pointer"
                    onClick={() => toggleDefaultSelection(source.id)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            checked={selectedDefaults.has(source.id)}
                            onChange={() => toggleDefaultSelection(source.id)}
                            className="rounded text-blue-600"
                            onClick={(e) => e.stopPropagation()}
                          />
                          <h5 className="font-medium text-gray-900 text-sm">{source.name}</h5>
                        </div>
                        {source.description && (
                          <p className="text-xs text-gray-600 mt-1 ml-6">{source.description}</p>
                        )}
                        {source.category && (
                          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded mt-2 ml-6 inline-block">
                            {source.category}
                          </span>
                        )}
                      </div>
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-400 hover:text-blue-600 ml-2"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedDefaults.size > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                <CheckCircle className="h-4 w-4 inline mr-2" />
                {selectedDefaults.size} default source{selectedDefaults.size > 1 ? 's' : ''} selected.
                These will be available when creating a new brand.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Custom Sources Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-2">
                <Plus className="h-5 w-5 text-green-600" />
                <h3 className="text-lg font-semibold text-gray-900">Custom Sources</h3>
              </div>
              <p className="text-sm text-gray-600 mt-1">
                Add your own custom sources for brand-specific monitoring
              </p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition text-sm"
            >
              Add Custom Source
            </button>
          </div>
        </div>

        <div className="p-6">
          {customSources.length === 0 ? (
            <div className="text-center py-12">
              <Plus className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-gray-900 mb-2">No Custom Sources Yet</h4>
              <p className="text-gray-600 mb-4">
                Add custom sources to monitor brand-specific communities
              </p>
              <button
                onClick={() => setShowAddModal(true)}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition"
              >
                Add Your First Custom Source
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {customSources.map((source) => (
                <div
                  key={source.id}
                  className="border border-gray-200 rounded-lg p-4 hover:border-green-300 transition"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <Globe className="h-5 w-5 text-green-600" />
                      <h5 className="font-medium text-gray-900">{source.name}</h5>
                    </div>
                    <button
                      onClick={() => handleDeleteCustomSource(source.id)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash className="h-4 w-4" />
                    </button>
                  </div>

                  {source.description && (
                    <p className="text-sm text-gray-600 mb-2">{source.description}</p>
                  )}

                  <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                    <span className="bg-gray-100 px-2 py-1 rounded">{source.platform}</span>
                    {source.category && (
                      <span className="bg-green-100 text-green-700 px-2 py-1 rounded">
                        {source.category}
                      </span>
                    )}
                  </div>

                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:text-blue-700 flex items-center space-x-1"
                  >
                    <span className="truncate">{source.url}</span>
                    <ExternalLink className="h-3 w-3 flex-shrink-0" />
                  </a>

                  {source.created_at && (
                    <p className="text-xs text-gray-400 mt-2">
                      Added {new Date(source.created_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add Source Modal */}
      {showAddModal && (
        <AddSourceModal
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false);
            fetchSources();
          }}
        />
      )}
    </div>
  );
}
