'use client';

import React, { useState, useEffect } from 'react';
import { apiService } from '@/lib/api';

interface Brand {
  id: string;
  name: string;
  brand_analytics: {
    campaigns: number;
    communities: number;
    threads: number;
    pain_points: number;
  };
  custom_campaigns: Array<{
    id: string;
    name: string;
    threads: number;
    pain_points: number;
    communities: number;
  }>;
}

interface DeleteResponse {
  success: boolean;
  message: string;
  deleted_counts: {
    threads?: number;
    pain_points?: number;
    communities?: number;
    influencers?: number;
  };
}

const DeleteData: React.FC = () => {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrand, setSelectedBrand] = useState<string>('');
  const [deleteType, setDeleteType] = useState<'brand_analytics' | 'campaign'>('brand_analytics');
  const [selectedCampaign, setSelectedCampaign] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [fetchingBrands, setFetchingBrands] = useState(true);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  // Fetch brands data
  useEffect(() => {
    fetchBrands();
  }, []);

  const fetchBrands = async () => {
    setFetchingBrands(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/admin/delete-data/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setBrands(data.brands);
      } else {
        throw new Error('Failed to fetch brands');
      }
    } catch (error) {
      console.error('Error fetching brands:', error);
      setMessage({ type: 'error', text: 'Failed to load brands data' });
    } finally {
      setFetchingBrands(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedBrand) {
      setMessage({ type: 'error', text: 'Please select a brand' });
      return;
    }

    if (deleteType === 'campaign' && !selectedCampaign) {
      setMessage({ type: 'error', text: 'Please select a campaign' });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const response = await fetch('http://localhost:8000/api/v1/admin/delete-data/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          brand_id: selectedBrand,
          delete_type: deleteType,
          campaign_id: deleteType === 'campaign' ? selectedCampaign : undefined,
        }),
      });

      const data: DeleteResponse = await response.json();

      if (response.ok && data.success) {
        setMessage({
          type: 'success',
          text: `${data.message}\n\nDeleted:\n- Threads: ${data.deleted_counts.threads || 0}\n- Pain Points: ${data.deleted_counts.pain_points || 0}\n- Communities: ${data.deleted_counts.communities || 0}${data.deleted_counts.influencers ? `\n- Influencers: ${data.deleted_counts.influencers}` : ''}`,
        });
        // Refresh brands data
        await fetchBrands();
        setSelectedBrand('');
        setSelectedCampaign('');
        setShowConfirmModal(false);
      } else {
        throw new Error(data.message || 'Failed to delete data');
      }
    } catch (error) {
      console.error('Error deleting data:', error);
      setMessage({ type: 'error', text: error instanceof Error ? error.message : 'Failed to delete data' });
      setShowConfirmModal(false);
    } finally {
      setLoading(false);
    }
  };

  const selectedBrandData = brands.find(b => b.id === selectedBrand);
  const selectedCampaignData = selectedBrandData?.custom_campaigns.find(c => c.id === selectedCampaign);

  const getDeleteSummary = () => {
    if (!selectedBrandData) return null;

    if (deleteType === 'brand_analytics') {
      return (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded">
          <h3 className="font-semibold text-red-800 mb-2">⚠️ This will delete:</h3>
          <ul className="text-sm text-red-700 space-y-1">
            <li>• {selectedBrandData.brand_analytics.campaigns} automatic campaign(s)</li>
            <li>• {selectedBrandData.brand_analytics.communities} communities</li>
            <li>• {selectedBrandData.brand_analytics.threads} threads</li>
            <li>• {selectedBrandData.brand_analytics.pain_points} pain points</li>
            <li>• All influencers for this brand</li>
          </ul>
        </div>
      );
    } else if (selectedCampaignData) {
      return (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded">
          <h3 className="font-semibold text-red-800 mb-2">⚠️ This will delete from "{selectedCampaignData.name}":</h3>
          <ul className="text-sm text-red-700 space-y-1">
            <li>• {selectedCampaignData.communities} communities</li>
            <li>• {selectedCampaignData.threads} threads</li>
            <li>• {selectedCampaignData.pain_points} pain points</li>
          </ul>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6">
      {fetchingBrands ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">Loading brands...</p>
        </div>
      ) : (
        <>
          {/* Brand Selection */}
          <div>
                <label htmlFor="brand" className="block text-sm font-medium text-gray-700 mb-2">
                  Select Brand *
                </label>
                <select
                  id="brand"
                  value={selectedBrand}
                  onChange={(e) => {
                    setSelectedBrand(e.target.value);
                    setSelectedCampaign('');
                    setMessage(null);
                  }}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">-- Select a brand --</option>
                  {brands.map((brand) => (
                    <option key={brand.id} value={brand.id}>
                      {brand.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Delete Type Selection */}
              {selectedBrand && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    What to Delete *
                  </label>
                  <div className="space-y-3">
                    <label className="flex items-start p-4 border-2 border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                      <input
                        type="radio"
                        value="brand_analytics"
                        checked={deleteType === 'brand_analytics'}
                        onChange={(e) => {
                          setDeleteType(e.target.value as 'brand_analytics');
                          setSelectedCampaign('');
                          setMessage(null);
                        }}
                        className="mt-1 mr-3"
                      />
                      <div>
                        <div className="font-medium text-gray-900">Brand Analytics Data</div>
                        <div className="text-sm text-gray-600">
                          Delete all automatic campaign data (communities, threads, pain points, influencers)
                        </div>
                      </div>
                    </label>

                    <label className="flex items-start p-4 border-2 border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                      <input
                        type="radio"
                        value="campaign"
                        checked={deleteType === 'campaign'}
                        onChange={(e) => {
                          setDeleteType(e.target.value as 'campaign');
                          setMessage(null);
                        }}
                        className="mt-1 mr-3"
                      />
                      <div>
                        <div className="font-medium text-gray-900">Custom Campaign Data</div>
                        <div className="text-sm text-gray-600">
                          Delete data from a specific custom campaign
                        </div>
                      </div>
                    </label>
                  </div>
                </div>
              )}

              {/* Campaign Selection (if delete type is campaign) */}
              {selectedBrand && deleteType === 'campaign' && selectedBrandData && (
                <div>
                  <label htmlFor="campaign" className="block text-sm font-medium text-gray-700 mb-2">
                    Select Campaign *
                  </label>
                  {selectedBrandData.custom_campaigns.length === 0 ? (
                    <p className="text-sm text-gray-500 italic">No custom campaigns found for this brand</p>
                  ) : (
                    <select
                      id="campaign"
                      value={selectedCampaign}
                      onChange={(e) => {
                        setSelectedCampaign(e.target.value);
                        setMessage(null);
                      }}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="">-- Select a campaign --</option>
                      {selectedBrandData.custom_campaigns.map((campaign) => (
                        <option key={campaign.id} value={campaign.id}>
                          {campaign.name} ({campaign.threads} threads, {campaign.pain_points} pain points)
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              {/* Delete Summary */}
              {getDeleteSummary()}

              {/* Action Buttons */}
              {selectedBrand && (deleteType === 'brand_analytics' || selectedCampaign) && (
                <div className="flex gap-4 pt-4">
                  <button
                    onClick={() => setShowConfirmModal(true)}
                    disabled={loading}
                    className="flex-1 bg-red-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                  >
                    {loading ? 'Deleting...' : 'Delete Data'}
                  </button>
                  <button
                    onClick={() => {
                      setSelectedBrand('');
                      setSelectedCampaign('');
                      setMessage(null);
                    }}
                    disabled={loading}
                    className="px-6 py-3 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              )}

              {/* Message Display */}
              {message && (
                <div
                  className={`mt-6 p-4 rounded-lg ${
                    message.type === 'success'
                      ? 'bg-green-50 border border-green-200 text-green-800'
                      : 'bg-red-50 border border-red-200 text-red-800'
                  }`}
                >
                  <pre className="whitespace-pre-wrap font-sans text-sm">{message.text}</pre>
                </div>
              )}
            </>
          )}

        {/* Confirmation Modal */}
        {showConfirmModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-8 max-w-md mx-4">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">⚠️ Confirm Deletion</h2>
              <p className="text-gray-700 mb-6">
                This action cannot be undone. Are you sure you want to permanently delete this data?
              </p>
              <div className="flex gap-4">
                <button
                  onClick={handleDelete}
                  disabled={loading}
                  className="flex-1 bg-red-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-red-700 disabled:bg-gray-400 transition-colors"
                >
                  {loading ? 'Deleting...' : 'Yes, Delete'}
                </button>
                <button
                  onClick={() => setShowConfirmModal(false)}
                  disabled={loading}
                  className="flex-1 border border-gray-300 px-6 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
  );
};

export default DeleteData;
