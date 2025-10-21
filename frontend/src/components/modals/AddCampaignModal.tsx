import { useState } from 'react';
import { apiService } from '@/lib/api';
import { X, Loader2, Search, CheckCircle, AlertCircle, Calendar, Target, Zap } from 'lucide-react';

interface AddCampaignModalProps {
  onClose: () => void;
  onCampaignAdded: () => void;
  brandId: string | null;
}

export function AddCampaignModal({ onClose, onCampaignAdded, brandId }: AddCampaignModalProps) {
  const [formData, setFormData] = useState({
    // Basic campaign info
    name: '',
    description: '',
    budget: '',
    startDate: '',
    endDate: '',
    
    // Enhanced scout-specific fields for campaign analysis
    campaign_keywords: '',
    target_communities: '',
    scout_focus: 'campaign_performance',
    search_depth: 'comprehensive',
    include_sentiment: true,
    include_competitors: true,
    focus_areas: ['campaign_mentions', 'audience_response', 'sentiment'] as string[]
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [scoutStatus, setScoutStatus] = useState<'idle' | 'analyzing' | 'completed' | 'failed'>('idle');
  const [scoutResults, setScoutResults] = useState<any>(null);
  const [error, setError] = useState('');

  const handleFocusAreaChange = (area: string, checked: boolean) => {
    if (checked) {
      setFormData({
        ...formData,
        focus_areas: [...formData.focus_areas, area]
      });
    } else {
      setFormData({
        ...formData,
        focus_areas: formData.focus_areas.filter(a => a !== area)
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!brandId) {
      setError('Please select a brand first');
      return;
    }

    if (!formData.name.trim()) return;

    setIsLoading(true);
    setScoutStatus('analyzing');
    setError('');

    try {
      console.log('🚀 Creating campaign with scout analysis...');
      
      // Prepare enhanced keywords for campaign analysis
      const campaignKeywords = formData.campaign_keywords 
        ? formData.campaign_keywords.split(',').map(k => k.trim()).filter(k => k)
        : [formData.name, 'campaign', 'marketing', 'promotion', 'advertisement', 'feedback'];

      // Prepare target communities
      const targetCommunities = formData.target_communities
        ? formData.target_communities.split(',').map(c => c.trim()).filter(c => c)
        : [];

      const campaignData = {
        name: formData.name,
        description: formData.description,
        brand: brandId,
        budget: parseFloat(formData.budget),
        start_date: formData.startDate,
        end_date: formData.endDate,
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

      // Create campaign with scout analysis (using apiService to match brand modal)
      const result = await apiService.createCampaign(campaignData);
      
      console.log('✅ Campaign created with scout analysis:', result);
      
      // Update UI based on result
      if (result.scout_analysis) {
        setScoutResults(result.scout_analysis);
        setScoutStatus(result.scout_analysis.analysis_status === 'completed' ? 'completed' : 'failed');
      } else {
        setScoutStatus('completed');
      }

      onCampaignAdded();
      
      setTimeout(() => {
        onClose();
        resetForm();
      }, scoutStatus === 'completed' ? 3000 : 2000);

    } catch (error: any) {
      console.error('❌ Campaign creation failed:', error);
      setError(error.response?.data?.error || 'Failed to create campaign');
      setScoutStatus('failed');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      budget: '',
      startDate: '',
      endDate: '',
      campaign_keywords: '',
      target_communities: '',
      scout_focus: 'campaign_performance',
      search_depth: 'comprehensive',
      include_sentiment: true,
      include_competitors: true,
      focus_areas: ['campaign_mentions', 'audience_response', 'sentiment']
    });
    setScoutStatus('idle');
    setScoutResults(null);
    setError('');
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity bg-gray-500 bg-opacity-75" onClick={onClose}></div>

        <div className="inline-block w-full max-w-2xl p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-lg max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-2">
              <Target className="h-5 w-5 text-green-600" />
              <h3 className="text-lg font-medium text-gray-900">Add New Campaign</h3>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600" disabled={isLoading}>
              <X className="h-6 w-6" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Campaign Information */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="font-medium text-gray-900 mb-4 flex items-center">
                <Calendar className="h-4 w-4 mr-2" />
                Campaign Information
              </h4>
              
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                    Campaign Name *
                  </label>
                  <input
                    type="text"
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="Enter campaign name"
                    required
                  />
                </div>

                <div>
                  <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="Describe your campaign goals and strategy"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label htmlFor="budget" className="block text-sm font-medium text-gray-700 mb-1">
                      Budget (USD)
                    </label>
                    <input
                      type="number"
                      id="budget"
                      value={formData.budget}
                      onChange={(e) => setFormData({...formData, budget: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      placeholder="10000"
                      min="0"
                      step="0.01"
                    />
                  </div>

                  <div>
                    <label htmlFor="startDate" className="block text-sm font-medium text-gray-700 mb-1">
                      Start Date *
                    </label>
                    <input
                      type="date"
                      id="startDate"
                      value={formData.startDate}
                      onChange={(e) => setFormData({...formData, startDate: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div>
                    <label htmlFor="endDate" className="block text-sm font-medium text-gray-700 mb-1">
                      End Date *
                    </label>
                    <input
                      type="date"
                      id="endDate"
                      value={formData.endDate}
                      onChange={(e) => setFormData({...formData, endDate: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      required
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Enhanced Scout Configuration */}
            <div className="bg-green-50 p-4 rounded-lg border border-green-200">
              <h4 className="font-medium text-gray-900 mb-4 flex items-center">
                <Search className="h-4 w-4 mr-2 text-green-600" />
                Campaign Intelligence & Analysis
              </h4>
              
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="campaign_keywords" className="block text-sm font-medium text-gray-700 mb-1">
                      Campaign Keywords
                    </label>
                    <input
                      type="text"
                      id="campaign_keywords"
                      value={formData.campaign_keywords}
                      onChange={(e) => setFormData({...formData, campaign_keywords: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      placeholder="campaign name, product, promotion (comma-separated)"
                    />
                    <p className="text-xs text-gray-500 mt-1">Keywords to search for campaign mentions and discussions</p>
                  </div>

                  <div>
                    <label htmlFor="target_communities" className="block text-sm font-medium text-gray-700 mb-1">
                      Target Communities
                    </label>
                    <input
                      type="text"
                      id="target_communities"
                      value={formData.target_communities}
                      onChange={(e) => setFormData({...formData, target_communities: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                      placeholder="marketing, advertising, socialmedia (comma-separated)"
                    />
                    <p className="text-xs text-gray-500 mt-1">Specific communities or subreddits to focus on</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="scout_focus" className="block text-sm font-medium text-gray-700 mb-1">
                      Analysis Focus
                    </label>
                    <select
                      id="scout_focus"
                      value={formData.scout_focus}
                      onChange={(e) => setFormData({...formData, scout_focus: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    >
                      <option value="campaign_performance">Campaign Performance</option>
                      <option value="audience_response">Audience Response</option>
                      <option value="competitive_analysis">Competitive Analysis</option>
                      <option value="comprehensive">Comprehensive Analysis</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor="search_depth" className="block text-sm font-medium text-gray-700 mb-1">
                      Search Depth
                    </label>
                    <select
                      id="search_depth"
                      value={formData.search_depth}
                      onChange={(e) => setFormData({...formData, search_depth: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    >
                      <option value="quick">Quick Scan</option>
                      <option value="standard">Standard Analysis</option>
                      <option value="comprehensive">Comprehensive Deep-Dive</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Analysis Focus Areas
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {[
                      { key: 'campaign_mentions', label: 'Campaign Mentions' },
                      { key: 'audience_response', label: 'Audience Response' },
                      { key: 'sentiment', label: 'Sentiment Analysis' },
                      { key: 'engagement', label: 'Engagement Metrics' },
                      { key: 'competitive_ads', label: 'Competitive Ads' },
                      { key: 'conversion_discussion', label: 'Conversion Talk' },
                      { key: 'feedback', label: 'User Feedback' },
                      { key: 'reach_analysis', label: 'Reach Analysis' }
                    ].map((area) => (
                      <label key={area.key} className="flex items-center space-x-2 text-sm">
                        <input
                          type="checkbox"
                          checked={formData.focus_areas.includes(area.key)}
                          onChange={(e) => handleFocusAreaChange(area.key, e.target.checked)}
                          className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                        />
                        <span className="text-gray-700">{area.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={formData.include_sentiment}
                      onChange={(e) => setFormData({...formData, include_sentiment: e.target.checked})}
                      className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                    />
                    <span className="text-sm font-medium text-gray-700">Include Sentiment Analysis</span>
                  </label>

                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={formData.include_competitors}
                      onChange={(e) => setFormData({...formData, include_competitors: e.target.checked})}
                      className="rounded border-gray-300 text-green-600 focus:ring-green-500"
                    />
                    <span className="text-sm font-medium text-gray-700">Include Competitor Analysis</span>
                  </label>
                </div>
              </div>
            </div>

            {/* Scout Status Display */}
            {scoutStatus !== 'idle' && (
              <div className="bg-white border rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-3">
                  {scoutStatus === 'analyzing' && <Loader2 className="h-4 w-4 animate-spin text-green-600" />}
                  {scoutStatus === 'completed' && <CheckCircle className="h-4 w-4 text-green-600" />}
                  {scoutStatus === 'failed' && <AlertCircle className="h-4 w-4 text-red-600" />}
                  <span className="font-medium">
                    {scoutStatus === 'analyzing' && 'Analyzing Campaign Intelligence...'}
                    {scoutStatus === 'completed' && 'Campaign Analysis Complete!'}
                    {scoutStatus === 'failed' && 'Analysis Failed'}
                  </span>
                </div>

                {scoutStatus === 'analyzing' && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm text-gray-600">
                      <span>Scanning campaign mentions and audience response...</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-green-600 h-2 rounded-full animate-pulse" style={{width: '60%'}}></div>
                    </div>
                  </div>
                )}

                {scoutStatus === 'completed' && scoutResults && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3">
                    <div className="text-center p-2 bg-green-50 rounded">
                      <div className="text-lg font-semibold text-green-600">
                        {scoutResults.communities_found || 0}
                      </div>
                      <div className="text-xs text-gray-600">Communities</div>
                    </div>
                    <div className="text-center p-2 bg-blue-50 rounded">
                      <div className="text-lg font-semibold text-blue-600">
                        {scoutResults.discussions_found || 0}
                      </div>
                      <div className="text-xs text-gray-600">Discussions</div>
                    </div>
                    <div className="text-center p-2 bg-purple-50 rounded">
                      <div className="text-lg font-semibold text-purple-600">
                        {scoutResults.sentiment_score || 'N/A'}
                      </div>
                      <div className="text-xs text-gray-600">Sentiment</div>
                    </div>
                    <div className="text-center p-2 bg-orange-50 rounded">
                      <div className="text-lg font-semibold text-orange-600">
                        {scoutResults.engagement_metrics || 0}
                      </div>
                      <div className="text-xs text-gray-600">Engagement</div>
                    </div>
                  </div>
                )}

                {scoutStatus === 'failed' && (
                  <div className="text-red-600 text-sm">
                    Campaign intelligence analysis encountered an issue. The campaign was still created successfully.
                  </div>
                )}
              </div>
            )}

            {/* Error Display */}
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

            {/* Action Buttons */}
            <div className="flex justify-end space-x-3 pt-6 border-t">
              <button
                type="button"
                onClick={onClose}
                disabled={isLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading || !formData.name.trim() || !brandId}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Creating Campaign...</span>
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" />
                    <span>Create Campaign with Analysis</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}