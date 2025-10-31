'use client';

import { useState, useEffect } from 'react';
import {
  Plus,
  Edit,
  Trash,
  Globe,
  Building,
  Search,
  ExternalLink,
  Play,
  Square,
  Loader2
} from 'lucide-react';
import { AddBrandModal } from '../modals/AddBrandModal';
import { apiService } from '@/lib/api';


interface Brand {
  id: string;
  name: string;
  description: string;
  website: string;
  industry: string;
  campaign_count: number;
  created_at: string;
  analysis_status?: string;
  has_active_auto_campaign?: boolean;
}

export default function BrandManager() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [industryFilter, setIndustryFilter] = useState<string>('all');
  const [analysisOperations, setAnalysisOperations] = useState<{ [key: string]: boolean }>({});


  useEffect(() => {
    fetchBrands();
  }, []);

  const fetchBrands = async () => {
    try {
      setLoading(true);
      const data = await apiService.getBrands();
      setBrands(data.results || data.brands || []);
    } catch (error) {
      console.error('Failed to fetch brands:', error);
      setBrands([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteBrand = async (brandId: string) => {
    if (!confirm('Are you sure you want to delete this brand? This will also affect all related campaigns.')) return;

    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      await fetch(`${API_BASE_URL}/api/v1/brands/${brandId}/`, { method: 'DELETE' });
      setBrands(brands.filter(b => b.id !== brandId));
    } catch (error) {
      console.error('Failed to delete brand:', error);
    }
  };

  const handleAnalysisControl = async (brandId: string, action: 'start' | 'stop') => {
    try {
      setAnalysisOperations(prev => ({ ...prev, [brandId]: true }));

      await apiService.controlBrandAnalysis(brandId, action);

      // Refresh brands data after starting/stopping analytics
      setTimeout(() => {
        fetchBrands();
      }, 1500);

    } catch (error) {
      console.error(`Failed to ${action} analysis:`, error);
      alert(`Failed to ${action} brand analytics. Please try again.`);
    } finally {
      setAnalysisOperations(prev => ({ ...prev, [brandId]: false }));
    }
  };

  const filteredBrands = brands.filter(brand => {
    const matchesSearch = brand.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         brand.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesIndustry = industryFilter === 'all' || brand.industry === industryFilter;
    return matchesSearch && matchesIndustry;
  });

  const uniqueIndustries = [...new Set(brands.map(b => b.industry).filter(Boolean))];

  const getAnalysisStatusColor = (status?: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'paused':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getAnalysisStatusText = (status?: string) => {
    switch (status) {
      case 'completed':
        return 'Analysis Complete';
      case 'running':
        return 'Analyzing...';
      case 'failed':
        return 'Analysis Failed';
      case 'paused':
        return 'Analysis Paused';
      default:
        return 'Not Started';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading brands...</span>
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
              placeholder="Search brands..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <select
            value={industryFilter}
            onChange={(e) => setIndustryFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Industries</option>
            {uniqueIndustries.map(industry => (
              <option key={industry} value={industry}>{industry}</option>
            ))}
          </select>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          <Plus className="h-4 w-4" />
          <span>Add Brand</span>
        </button>
      </div>

      {/* Brands Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredBrands.map((brand) => (
          <div key={brand.id} className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
            <div className="p-6">
              {/* Brand Header */}
              <div className="mb-4">
                <h3 className="text-lg font-medium text-gray-900 mb-1 flex items-center">
                  <Building className="h-5 w-5 text-gray-400 mr-2" />
                  {brand.name}
                </h3>
                <p className="text-sm text-gray-600 line-clamp-2">
                  {brand.description}
                </p>
                {brand.industry && (
                  <span className="inline-block mt-2 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                    {brand.industry}
                  </span>
                )}
              </div>

              {/* Brand Details */}
              <div className="space-y-3 mb-4">
                {brand.website && (
                  <div className="flex items-center text-sm text-gray-600">
                    <Globe className="h-4 w-4 mr-2" />
                    <a 
                      href={brand.website} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-700 flex items-center"
                    >
                      Website <ExternalLink className="h-3 w-3 ml-1" />
                    </a>
                  </div>
                )}

                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Active Campaigns</span>
                  <span className="text-gray-900 font-medium">{brand.campaign_count}</span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between pt-4 border-t border-gray-200">
                <div className="flex items-center space-x-2">
                  {/* Start/Stop Analytics Button - Left Side */}
                  {brand.has_active_auto_campaign ? (
                    <button
                      onClick={() => handleAnalysisControl(brand.id, 'stop')}
                      disabled={analysisOperations[brand.id]}
                      className="flex items-center space-x-1 px-3 py-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {analysisOperations[brand.id] ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span className="text-xs">Stopping...</span>
                        </>
                      ) : (
                        <>
                          <Square className="h-4 w-4" />
                          <span className="text-xs">Stop Analytics</span>
                        </>
                      )}
                    </button>
                  ) : (
                    <button
                      onClick={() => handleAnalysisControl(brand.id, 'start')}
                      disabled={analysisOperations[brand.id]}
                      className="flex items-center space-x-1 px-3 py-2 text-green-600 hover:text-green-700 hover:bg-green-50 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {analysisOperations[brand.id] ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span className="text-xs">Starting...</span>
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4" />
                          <span className="text-xs">Start Analytics</span>
                        </>
                      )}
                    </button>
                  )}
                </div>

                <div className="flex items-center space-x-2">
                  {/* Edit and Delete - Right Side */}
                  <button
                    onClick={() => setEditingBrand(brand)}
                    className="flex items-center space-x-1 px-2 py-1 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded transition-colors"
                  >
                    <Edit className="h-4 w-4" />
                    <span className="text-xs">Edit</span>
                  </button>

                  <button
                    onClick={() => handleDeleteBrand(brand.id)}
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

      {filteredBrands.length === 0 && (
        <div className="text-center py-12">
          <Building className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No brands found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {searchTerm || industryFilter !== 'all'
              ? 'Try adjusting your search or filter criteria.'
              : 'Get started by adding your first brand to monitor.'
            }
          </p>
          {!searchTerm && industryFilter === 'all' && (
            <div className="mt-6">
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Brand
              </button>
            </div>
          )}
        </div>
      )}

      {/* Add Brand Modal */}
      {showCreateModal && (
        <AddBrandModal
          onClose={() => setShowCreateModal(false)}
          onBrandAdded={() => {
            setShowCreateModal(false);
            fetchBrands(); // Refresh brands list after successful creation
          }}
        />
      )}

      {/* Edit Brand Modal */}
      {editingBrand && (
        <AddBrandModal
          onClose={() => setEditingBrand(null)}
          onBrandAdded={() => {
            setEditingBrand(null);
            fetchBrands(); // Refresh brands list after edit
          }}
          editBrand={editingBrand}
        />
      )}
    </div>
  );
}