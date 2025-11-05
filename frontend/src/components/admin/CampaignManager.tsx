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
  Users,
  Building
} from 'lucide-react';
import { AddCampaignModal } from '../modals/AddCampaignModal';
import api from '@/lib/api';
import { formatCampaignDateTime, formatScheduleFrequency, getNextScheduledRun } from '@/lib/utils';

interface Campaign {
  id: string;
  name: string;
  description: string;
  brand?: string;
  brand_name?: string;
  status: 'active' | 'paused' | 'completed' | 'error';
  keywords: string[] | string;  // Can be array or string
  owner: number;
  schedule_enabled: boolean;
  schedule_interval: number;
  budget_limit: number;
  current_spend: number;
  created_at: string;
  start_date?: string;
  end_date?: string;
  last_run_at?: string;
  next_run_at?: string;
  is_auto_campaign?: boolean;  // Flag for automatic brand analytics campaigns
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
      // Fetch campaigns from API
      const response = await api.get('/campaigns/');
      setCampaigns(response.data.campaigns || []);
    } catch (error) {
      console.error('Failed to fetch campaigns:', error);
      setCampaigns([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (campaignId: string, newStatus: string) => {
    try {
      // Update campaign status via API
      await api.put(`/campaigns/${campaignId}/`, {
        status: newStatus
      });

      // Update local state after successful API call
      setCampaigns(campaigns.map(c =>
        c.id === campaignId ? { ...c, status: newStatus as any } : c
      ));
    } catch (error) {
      console.error('Failed to update campaign status:', error);
      alert('Failed to update campaign status. Please try again.');
    }
  };

  const handleDeleteCampaign = async (campaignId: string) => {
    if (!confirm('Are you sure you want to delete this campaign?')) return;

    try {
      // Delete campaign via API
      await api.delete(`/campaigns/${campaignId}/`);
      // Remove from local state after successful deletion
      setCampaigns(campaigns.filter(c => c.id !== campaignId));
    } catch (error) {
      console.error('Failed to delete campaign:', error);
      alert('Failed to delete campaign. Please try again.');
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
      case 'paused': return 'bg-gray-100 text-gray-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active': return 'Active';
      case 'paused': return 'Inactive';
      case 'completed': return 'Completed';
      case 'error': return 'Error';
      default: return 'Inactive';
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
    <div className="w-full space-y-6">
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
          <div key={campaign.id} className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
            {/* Ribbon Badge */}
            {campaign.is_auto_campaign ? (
              <div className="absolute top-0 right-0">
                <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white text-xs font-semibold px-3 py-1 shadow-md">
                  AUTOMATIC
                </div>
              </div>
            ) : (
              <div className="absolute top-0 right-0">
                <div className="bg-gradient-to-r from-green-500 to-green-600 text-white text-xs font-semibold px-3 py-1 shadow-md">
                  CUSTOM
                </div>
              </div>
            )}

            <div className="p-6 pt-10">
              {/* Campaign Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-medium text-gray-900 mb-1">
                    {campaign.name}
                  </h3>
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {campaign.description}
                  </p>
                  {campaign.brand_name && (
                    <div className="mt-2">
                      <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                        <Building className="h-3 w-3 mr-1" />
                        {campaign.brand_name}
                      </span>
                    </div>
                  )}
                </div>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(campaign.status)}`}>
                  {getStatusText(campaign.status)}
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

                {/* Timing Information */}
                <div className="space-y-2 pt-2 border-t border-gray-100">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Start Date:</span>
                    <span className="text-gray-700 font-medium">{formatCampaignDateTime(campaign.start_date)}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">End Date:</span>
                    <span className="text-gray-700 font-medium">{formatCampaignDateTime(campaign.end_date)}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Next Run:</span>
                    <span className="text-gray-700 font-medium">
                      {getNextScheduledRun(campaign.last_run_at, campaign.schedule_interval, campaign.schedule_enabled, campaign.next_run_at)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Frequency:</span>
                    <span className="text-gray-700 font-medium">{formatScheduleFrequency(campaign.schedule_interval)}</span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-4 border-t border-gray-200">
                <div className="flex items-center space-x-2">
                  {/* Start/Pause - Left Side */}
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
                </div>

                <div className="flex items-center space-x-2">
                  {/* Edit and Delete - Right Side (hidden for automatic campaigns) */}
                  {!campaign.is_auto_campaign && (
                    <>
                      <button
                        onClick={() => setEditingCampaign(campaign)}
                        className="flex items-center space-x-1 px-2 py-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
                      >
                        <Edit className="h-4 w-4" />
                        <span className="text-xs">Edit</span>
                      </button>

                      <button
                        onClick={() => handleDeleteCampaign(campaign.id)}
                        className="flex items-center space-x-1 px-2 py-1 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors"
                      >
                        <Trash className="h-4 w-4" />
                        <span className="text-xs">Delete</span>
                      </button>
                    </>
                  )}
                  {campaign.is_auto_campaign && (
                    <span className="text-xs text-gray-500 italic">Managed by Brand</span>
                  )}
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

      {/* Create Campaign Modal */}
      {showCreateModal && (
        <AddCampaignModal
          onClose={() => setShowCreateModal(false)}
          onCampaignAdded={() => {
            setShowCreateModal(false);
            fetchCampaigns(); // Refresh campaigns list after successful creation
          }}
          brandId={null} // Or pass a specific brandId if you want to pre-select one
        />
      )}

      {/* Edit Campaign Modal */}
      {editingCampaign && (
        <AddCampaignModal
          onClose={() => setEditingCampaign(null)}
          onCampaignAdded={() => {
            setEditingCampaign(null);
            fetchCampaigns(); // Refresh campaigns list after edit
          }}
          editCampaign={editingCampaign}
          brandId={editingCampaign.brand || null}
        />
      )}
    </div>
  );
}