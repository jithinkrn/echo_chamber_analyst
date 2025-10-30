import { useState, useEffect } from 'react';
import { apiService } from '@/lib/api';
import { X, Loader2, CheckCircle, AlertCircle, Target } from 'lucide-react';

interface AddCampaignModalProps {
  onClose: () => void;
  onCampaignAdded: () => void;
  brandId: string | null;
  editCampaign?: any;  // Campaign to edit (if provided)
}

export function AddCampaignModal({ onClose, onCampaignAdded, brandId, editCampaign }: AddCampaignModalProps) {
  const [formData, setFormData] = useState({
    name: editCampaign?.name || '',
    description: editCampaign?.description || '',
    budget: editCampaign?.daily_budget?.toString() || '',
    budget_limit: editCampaign?.budget_limit?.toString() || '',
    startDate: editCampaign?.start_date ? editCampaign.start_date.slice(0, 16) : '',
    endDate: editCampaign?.end_date ? editCampaign.end_date.slice(0, 16) : '',
    selectedBrandId: editCampaign?.brand || brandId || '',
    campaign_keywords: Array.isArray(editCampaign?.keywords) ? editCampaign.keywords.join(', ') : (editCampaign?.keywords || ''),
    target_communities: '',
    scout_focus: 'campaign_performance',
    search_depth: 'comprehensive',
    include_sentiment: true,
    include_competitors: true,
    focus_areas: ['campaign_mentions', 'audience_response', 'sentiment'] as string[]
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [brands, setBrands] = useState<any[]>([]);
  const [loadingBrands, setLoadingBrands] = useState(false);

  useEffect(() => {
    const loadBrands = async () => {
      setLoadingBrands(true);
      try {
        const response = await apiService.getBrands();
        setBrands(response.results || response || []);
      } catch (error) {
        console.error('Failed to load brands:', error);
        setError('Failed to load brands. Please try again.');
      } finally {
        setLoadingBrands(false);
      }
    };

    loadBrands();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.selectedBrandId) {
      setError('Please select a brand first');
      return;
    }

    if (!formData.name.trim()) {
      setError('Please enter a campaign name');
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      const campaignKeywords = formData.campaign_keywords
        ? formData.campaign_keywords.split(',').map(k => k.trim()).filter(k => k)
        : [formData.name, 'campaign', 'marketing', 'promotion'];

      const targetCommunities = formData.target_communities
        ? formData.target_communities.split(',').map(c => c.trim()).filter(c => c)
        : [];

      const campaignData = {
        name: formData.name,
        description: formData.description,
        brand: formData.selectedBrandId,
        budget: parseFloat(formData.budget) || 0,
        budget_limit: formData.budget_limit ? parseFloat(formData.budget_limit) : null,
        start_date: formData.startDate ? new Date(formData.startDate).toISOString() : null,
        end_date: formData.endDate ? new Date(formData.endDate).toISOString() : null,
        schedule_enabled: true,  // Enable scheduling by default for custom campaigns
        keywords: campaignKeywords,
        scout_config: {
          focus: formData.scout_focus,
          search_depth: formData.search_depth,
          target_communities: targetCommunities,
          include_sentiment: formData.include_sentiment,
          include_competitors: formData.include_competitors,
          focus_areas: formData.focus_areas
        }
      };

      if (editCampaign) {
        // Update existing campaign
        await apiService.updateCampaign(editCampaign.id, campaignData);
      } else {
        // Create new campaign
        await apiService.createCampaign(campaignData);
      }

      onCampaignAdded();
      onClose();

    } catch (error: any) {
      console.error(`Campaign ${editCampaign ? 'update' : 'creation'} failed:`, error);
      setError(error.response?.data?.error || `Failed to ${editCampaign ? 'update' : 'create'} campaign`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center"
      style={{ zIndex: 9999 }}
      onClick={onClose}
    >
      <div
        className="bg-white p-6 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-2">
            <Target className="h-5 w-5 text-green-600" />
            <h3 className="text-lg font-medium text-gray-900">{editCampaign ? 'Edit Campaign' : 'Add New Campaign'}</h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" disabled={isLoading}>
            <X className="h-6 w-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="Enter campaign name"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Brand *</label>
            <select
              value={formData.selectedBrandId}
              onChange={(e) => setFormData({...formData, selectedBrandId: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              required
              disabled={loadingBrands}
            >
              <option value="">
                {loadingBrands ? 'Loading brands...' : 'Select a brand'}
              </option>
              {brands.map((brand) => (
                <option key={brand.id} value={brand.id}>
                  {brand.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              placeholder="Describe your campaign goals and strategy"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Daily Budget (USD)</label>
              <input
                type="number"
                value={formData.budget}
                onChange={(e) => setFormData({...formData, budget: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="10.00"
                min="0"
                step="0.01"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Total Budget Limit (USD)
                <span className="text-xs text-gray-500 ml-1">(optional - auto-completes when reached)</span>
              </label>
              <input
                type="number"
                value={formData.budget_limit}
                onChange={(e) => setFormData({...formData, budget_limit: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="100.00"
                min="0"
                step="0.01"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date & Time</label>
              <input
                type="datetime-local"
                value={formData.startDate}
                onChange={(e) => setFormData({...formData, startDate: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Date & Time
                <span className="text-xs text-gray-500 ml-1">(optional - auto-completes when reached)</span>
              </label>
              <input
                type="datetime-local"
                value={formData.endDate}
                onChange={(e) => setFormData({...formData, endDate: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="flex">
                <AlertCircle className="h-4 w-4 text-red-400 mt-0.5" />
                <div className="ml-2">
                  <h4 className="text-sm font-medium text-red-800">Error</h4>
                  <div className="mt-1 text-sm text-red-700">{error}</div>
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-6 border-t">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !formData.name.trim() || !formData.selectedBrandId}
              className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{editCampaign ? 'Updating Campaign...' : 'Creating Campaign...'}</span>
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4" />
                  <span>{editCampaign ? 'Update Campaign' : 'Create Campaign'}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}