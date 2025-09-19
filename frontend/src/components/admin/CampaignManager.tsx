'use client';

import { useState, useEffect } from 'react';
import {
  Plus,
  Edit,
  Trash,
  Play,
  Pause,
  BarChart,
  Search,
  Filter,
  Calendar,
  DollarSign,
  Users
} from 'lucide-react';

interface Campaign {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'paused' | 'completed' | 'draft';
  keywords: string;
  owner: number;
  schedule_enabled: boolean;
  schedule_interval: number;
  budget_limit: number;
  current_spend: number;
  created_at: string;
  last_run_at?: string;
  next_run_at?: string;
}

export default function CampaignManager() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      setLoading(true);
      // TODO: Replace with actual API call
      // const response = await apiService.getCampaigns();
      // setCampaigns(response.data.results);

      // Mock data for now
      setCampaigns([
        {
          id: '1',
          name: 'Reddit Echo Chamber Analysis',
          description: 'Analyzing political discourse in Reddit communities',
          status: 'active',
          keywords: 'politics, election, voting',
          owner: 1,
          schedule_enabled: true,
          schedule_interval: 3600,
          budget_limit: 100.00,
          current_spend: 25.50,
          created_at: '2025-09-15T10:00:00Z',
          last_run_at: '2025-09-18T08:00:00Z',
          next_run_at: '2025-09-18T12:00:00Z'
        },
        {
          id: '2',
          name: 'Social Media Sentiment Tracking',
          description: 'Monitoring sentiment trends across platforms',
          status: 'paused',
          keywords: 'sentiment, emotion, social',
          owner: 1,
          schedule_enabled: false,
          schedule_interval: 7200,
          budget_limit: 50.00,
          current_spend: 12.30,
          created_at: '2025-09-10T14:30:00Z'
        }
      ]);
    } catch (error) {
      console.error('Failed to fetch campaigns:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (campaignId: string, newStatus: string) => {
    try {
      // TODO: Replace with actual API call
      // await apiService.updateCampaignStatus(campaignId, newStatus);
      setCampaigns(campaigns.map(c =>
        c.id === campaignId ? { ...c, status: newStatus as any } : c
      ));
    } catch (error) {
      console.error('Failed to update campaign status:', error);
    }
  };

  const handleDeleteCampaign = async (campaignId: string) => {
    if (!confirm('Are you sure you want to delete this campaign?')) return;

    try {
      // TODO: Replace with actual API call
      // await apiService.deleteCampaign(campaignId);
      setCampaigns(campaigns.filter(c => c.id !== campaignId));
    } catch (error) {
      console.error('Failed to delete campaign:', error);
    }
  };

  const filteredCampaigns = campaigns.filter(campaign => {
    const matchesSearch = campaign.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         campaign.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || campaign.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'paused': return 'bg-yellow-100 text-yellow-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'draft': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading campaigns...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search campaigns..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="completed">Completed</option>
            <option value="draft">Draft</option>
          </select>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          <span>New Campaign</span>
        </button>
      </div>

      {/* Campaigns Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredCampaigns.map((campaign) => (
          <div key={campaign.id} className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
            <div className="p-6">
              {/* Campaign Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-medium text-gray-900 mb-1">
                    {campaign.name}
                  </h3>
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {campaign.description}
                  </p>
                </div>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(campaign.status)}`}>
                  {campaign.status}
                </span>
              </div>

              {/* Campaign Stats */}
              <div className="space-y-3 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Budget Usage</span>
                  <span className="text-gray-900">
                    ${campaign.current_spend.toFixed(2)} / ${campaign.budget_limit.toFixed(2)}
                  </span>
                </div>

                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${Math.min((campaign.current_spend / campaign.budget_limit) * 100, 100)}%` }}
                  ></div>
                </div>

                <div className="flex items-center justify-between text-sm text-gray-600">
                  <span>Keywords: {campaign.keywords.split(',').length}</span>
                  <span>Schedule: {campaign.schedule_enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-4 border-t border-gray-200">
                <div className="flex items-center space-x-2">
                  {campaign.status === 'active' ? (
                    <button
                      onClick={() => handleStatusChange(campaign.id, 'paused')}
                      className="flex items-center space-x-1 px-2 py-1 text-yellow-600 hover:text-yellow-700 hover:bg-yellow-50 rounded transition-colors"
                    >
                      <Pause className="h-4 w-4" />
                      <span className="text-xs">Pause</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => handleStatusChange(campaign.id, 'active')}
                      className="flex items-center space-x-1 px-2 py-1 text-green-600 hover:text-green-700 hover:bg-green-50 rounded transition-colors"
                    >
                      <Play className="h-4 w-4" />
                      <span className="text-xs">Start</span>
                    </button>
                  )}

                  <button
                    onClick={() => setEditingCampaign(campaign)}
                    className="flex items-center space-x-1 px-2 py-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
                  >
                    <Edit className="h-4 w-4" />
                    <span className="text-xs">Edit</span>
                  </button>
                </div>

                <div className="flex items-center space-x-2">
                  <button className="flex items-center space-x-1 px-2 py-1 text-gray-600 hover:text-gray-700 hover:bg-gray-50 rounded transition-colors">
                    <BarChart className="h-4 w-4" />
                    <span className="text-xs">Stats</span>
                  </button>

                  <button
                    onClick={() => handleDeleteCampaign(campaign.id)}
                    className="flex items-center space-x-1 px-2 py-1 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                  >
                    <Trash className="h-4 w-4" />
                    <span className="text-xs">Delete</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredCampaigns.length === 0 && (
        <div className="text-center py-12">
          <BarChart className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No campaigns found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {searchTerm || statusFilter !== 'all'
              ? 'Try adjusting your search or filter criteria.'
              : 'Get started by creating a new campaign.'
            }
          </p>
          {!searchTerm && statusFilter === 'all' && (
            <div className="mt-6">
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <Plus className="h-4 w-4 mr-2" />
                New Campaign
              </button>
            </div>
          )}
        </div>
      )}

      {/* TODO: Add Create/Edit Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Create Campaign</h3>
            <p className="text-sm text-gray-600">Campaign creation form will be implemented here.</p>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}