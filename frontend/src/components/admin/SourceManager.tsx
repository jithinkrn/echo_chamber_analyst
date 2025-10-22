'use client';

import { useState, useEffect } from 'react';
import { Plus, Globe, Settings, Trash, CheckCircle, XCircle } from 'lucide-react';
import { AddSourceModal } from '../modals/AddSourceModal';

interface Source {
  id: string;
  name: string;
  url: string;
  source_type: 'reddit' | 'website' | 'api';
  is_active: boolean;
  last_accessed?: string;
  created_at: string;
}

export default function SourceManager() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    // Mock data for now
    setSources([
      {
        id: '1',
        name: 'Reddit Politics',
        url: 'https://reddit.com/r/politics',
        source_type: 'reddit',
        is_active: true,
        last_accessed: '2025-09-18T08:00:00Z',
        created_at: '2025-09-15T10:00:00Z'
      },
      {
        id: '2',
        name: 'News Website',
        url: 'https://example-news.com',
        source_type: 'website',
        is_active: false,
        created_at: '2025-09-10T14:30:00Z'
      }
    ]);
    setLoading(false);
  }, []);

  const fetchSources = () => {
    // Refresh sources list - this would typically reload from API
    console.log('Refreshing sources list...');
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
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">Content Sources</h3>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          <span>Add Source</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sources.map((source) => (
          <div key={source.id} className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center space-x-2">
                <Globe className="h-5 w-5 text-gray-400" />
                <h4 className="font-medium text-gray-900">{source.name}</h4>
              </div>
              {source.is_active ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-red-500" />
              )}
            </div>

            <p className="text-sm text-gray-600 mb-2">{source.url}</p>
            <p className="text-xs text-gray-500 mb-3">Type: {source.source_type}</p>

            {source.last_accessed && (
              <p className="text-xs text-gray-500 mb-3">
                Last accessed: {new Date(source.last_accessed).toLocaleDateString()}
              </p>
            )}

            <div className="flex justify-end space-x-2">
              <button className="text-blue-600 hover:text-blue-700">
                <Settings className="h-4 w-4" />
              </button>
              <button className="text-red-600 hover:text-red-700">
                <Trash className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Add Source Modal */}
      {showCreateModal && (
        <AddSourceModal
          onClose={() => setShowCreateModal(false)}
          onSourceAdded={() => {
            setShowCreateModal(false);
            fetchSources();
          }}
        />
      )}
    </div>
  );
}