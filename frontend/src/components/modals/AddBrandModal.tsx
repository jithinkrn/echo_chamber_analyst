'use client';

import { useState } from 'react';
import { apiService } from '@/lib/api';
import { X, Plus, Loader2, Search, CheckCircle, AlertCircle, Building, Target, Zap } from 'lucide-react';

interface AddBrandModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export function AddBrandModal({ onClose, onSuccess }: AddBrandModalProps) {
  const [formData, setFormData] = useState({
    // Basic brand info
    name: '',
    description: '',
    website: '',
    industry: '',
    
    // Enhanced scout-specific fields
    scout_keywords: '',
    target_communities: '',
    scout_focus: 'comprehensive',
    search_depth: 'comprehensive',
    include_sentiment: true,
    include_competitors: true,
    focus_areas: ['pain_points', 'feedback', 'sentiment'] as string[]
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
    if (!formData.name.trim()) return;

    setIsLoading(true);
    setScoutStatus('analyzing');
    setError('');

    try {
      console.log('🚀 Creating brand with enhanced scout configuration...');
      
      // Prepare enhanced keywords
      const scoutKeywords = formData.scout_keywords 
        ? formData.scout_keywords.split(',').map(k => k.trim()).filter(k => k)
        : [formData.name, 'review', 'quality', 'problems', 'complaint', 'feedback'];

      // Prepare target communities
      const targetCommunities = formData.target_communities
        ? formData.target_communities.split(',').map(c => c.trim()).filter(c => c)
        : [];

      // ✅ REPLACE EVERYTHING FROM HERE DOWN WITH THE SIMPLIFIED VERSION:
      const brandData = {
        name: formData.name,
        description: formData.description,
        website: formData.website,
        industry: formData.industry,
        keywords: scoutKeywords,  // Use the prepared keywords
        scout_config: {
          focus: formData.scout_focus,
          search_depth: formData.search_depth,
          target_communities: targetCommunities,  // Use the prepared communities
          include_sentiment: formData.include_sentiment,
          include_competitors: formData.include_competitors,
          focus_areas: formData.focus_areas
        }
      };

      // Single API call that creates brand AND triggers scout
      const result = await apiService.createBrand(brandData);
      
      console.log('✅ Brand created with scout analysis:', result);
      
      // Update UI based on result
      if (result.scout_analysis) {
        setScoutResults(result.scout_analysis);
        setScoutStatus(result.scout_analysis.analysis_status === 'completed' ? 'completed' : 'failed');
      } else {
        setScoutStatus('completed'); // Brand created successfully
      }

      onSuccess();
      
      setTimeout(() => {
        onClose();
        resetForm();
      }, scoutStatus === 'completed' ? 3000 : 2000);

    } catch (error: any) {
      console.error('❌ Brand creation failed:', error);
      setError(error.response?.data?.error || 'Failed to create brand');
      setScoutStatus('failed');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      website: '',
      industry: '',
      scout_keywords: '',
      target_communities: '',
      scout_focus: 'comprehensive',
      search_depth: 'comprehensive',
      include_sentiment: true,
      include_competitors: true,
      focus_areas: ['pain_points', 'feedback', 'sentiment']
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
              <Building className="h-5 w-5 text-blue-600" />
              <h3 className="text-lg font-medium text-gray-900">Add New Brand with Scout Analysis</h3>
            </div>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600" disabled={isLoading}>
              <X className="h-6 w-6" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Brand Information */}
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-md font-medium text-gray-900 mb-4 flex items-center">
                <Building className="h-4 w-4 mr-2" />
                Basic Brand Information
              </h4>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Brand Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Nike, Apple, Tesla"
                    required
                    disabled={isLoading}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Industry</label>
                  <input
                    type="text"
                    value={formData.industry}
                    onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Technology, Fashion, Automotive"
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={2}
                  placeholder="Brief description of the brand..."
                  disabled={isLoading}
                />
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700">Website</label>
                <input
                  type="url"
                  value={formData.website}
                  onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="https://example.com"
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Enhanced Scout Configuration */}
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <h4 className="text-md font-medium text-blue-900 mb-4 flex items-center">
                <Search className="h-4 w-4 mr-2" />
                Scout Analysis Configuration
              </h4>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-blue-800">Scout Keywords *</label>
                  <input
                    type="text"
                    value={formData.scout_keywords}
                    onChange={(e) => setFormData({ ...formData, scout_keywords: e.target.value })}
                    className="mt-1 block w-full border border-blue-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., quality issues, price complaints, customer service problems, product defects"
                    disabled={isLoading}
                  />
                  <p className="text-xs text-blue-600 mt-1">
                    🎯 Specific keywords to search for brand discussions (leave empty for auto-generated keywords)
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-blue-800">Analysis Focus</label>
                    <select
                      value={formData.scout_focus}
                      onChange={(e) => setFormData({ ...formData, scout_focus: e.target.value })}
                      className="mt-1 block w-full border border-blue-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={isLoading}
                    >
                      <option value="comprehensive">🔍 Comprehensive Analysis</option>
                      <option value="pain_points">⚠️ Focus on Pain Points</option>
                      <option value="sentiment">💭 Focus on Sentiment</option>
                      <option value="competitors">🏆 Focus on Competitors</option>
                      <option value="product_feedback">📝 Product Feedback Only</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-blue-800">Search Depth</label>
                    <select
                      value={formData.search_depth}
                      onChange={(e) => setFormData({ ...formData, search_depth: e.target.value })}
                      className="mt-1 block w-full border border-blue-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={isLoading}
                    >
                      <option value="quick">⚡ Quick Scan (5-10 mins)</option>
                      <option value="comprehensive">🔬 Comprehensive (15-20 mins)</option>
                      <option value="deep">🕳️ Deep Analysis (30+ mins)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-blue-800">Target Communities (Optional)</label>
                  <input
                    type="text"
                    value={formData.target_communities}
                    onChange={(e) => setFormData({ ...formData, target_communities: e.target.value })}
                    className="mt-1 block w-full border border-blue-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., r/technology, r/reviews, r/BuyItForLife"
                    disabled={isLoading}
                  />
                  <p className="text-xs text-blue-600 mt-1">
                    🎯 Specific Reddit communities to search (leave empty for auto-discovery)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-blue-800 mb-2">Analysis Features</label>
                  <div className="grid grid-cols-2 gap-2">
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.include_sentiment}
                        onChange={(e) => setFormData({ ...formData, include_sentiment: e.target.checked })}
                        className="rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                        disabled={isLoading}
                      />
                      <span className="text-sm text-blue-800">💭 Sentiment Analysis</span>
                    </label>
                    
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={formData.include_competitors}
                        onChange={(e) => setFormData({ ...formData, include_competitors: e.target.checked })}
                        className="rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                        disabled={isLoading}
                      />
                      <span className="text-sm text-blue-800">🏆 Competitor Detection</span>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-blue-800 mb-2">Focus Areas</label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {['pain_points', 'feedback', 'sentiment', 'pricing', 'quality', 'support'].map((area) => (
                      <label key={area} className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={formData.focus_areas.includes(area)}
                          onChange={(e) => handleFocusAreaChange(area, e.target.checked)}
                          className="rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                          disabled={isLoading}
                        />
                        <span className="text-sm text-blue-800 capitalize">
                          {area.replace('_', ' ')}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Scout Analysis Status */}
            {scoutStatus !== 'idle' && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg border">
                <div className="flex items-center space-x-2 mb-3">
                  {scoutStatus === 'analyzing' && (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                      <span className="text-sm font-medium text-blue-600">Running Enhanced Scout Analysis...</span>
                    </>
                  )}
                  {scoutStatus === 'completed' && (
                    <>
                      <CheckCircle className="h-5 w-5 text-green-600" />
                      <span className="text-sm font-medium text-green-600">Enhanced Scout Analysis Completed!</span>
                    </>
                  )}
                  {scoutStatus === 'failed' && (
                    <>
                      <AlertCircle className="h-5 w-5 text-orange-600" />
                      <span className="text-sm font-medium text-orange-600">Analysis incomplete, but brand was created</span>
                    </>
                  )}
                </div>

                {scoutStatus === 'analyzing' && (
                  <div className="text-xs text-gray-600 space-y-1">
                    <div>• 🔍 Searching with custom keywords: {formData.scout_keywords || 'auto-generated'}</div>
                    <div>• 🎯 Focus: {formData.scout_focus}</div>
                    <div>• 📊 Depth: {formData.search_depth}</div>
                    <div>• 🏢 Target communities: {formData.target_communities || 'auto-discovery'}</div>
                    <div>• 💭 Analyzing sentiment and pain points...</div>
                    <div>• 🏆 {formData.include_competitors ? 'Including competitor analysis' : 'Skipping competitors'}</div>
                  </div>
                )}

                {scoutResults && scoutResults.analysis_status === 'completed' && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                    <div className="bg-blue-100 p-3 rounded text-center">
                      <div className="text-xl font-bold text-blue-700">
                        {scoutResults.communities_found || scoutResults.data_collected?.communities || 0}
                      </div>
                      <div className="text-xs text-blue-600">Communities</div>
                    </div>
                    <div className="bg-green-100 p-3 rounded text-center">
                      <div className="text-xl font-bold text-green-700">
                        {scoutResults.threads_collected || scoutResults.data_collected?.threads || 0}
                      </div>
                      <div className="text-xs text-green-600">Discussions</div>
                    </div>
                    <div className="bg-orange-100 p-3 rounded text-center">
                      <div className="text-xl font-bold text-orange-700">
                        {scoutResults.pain_points_identified || scoutResults.data_collected?.pain_points || 0}
                      </div>
                      <div className="text-xs text-orange-600">Pain Points</div>
                    </div>
                    <div className="bg-purple-100 p-3 rounded text-center">
                      <div className="text-xl font-bold text-purple-700">
                        {scoutResults.brand_mentions || scoutResults.data_collected?.brand_mentions || 0}
                      </div>
                      <div className="text-xs text-purple-600">Brand Mentions</div>
                    </div>
                  </div>
                )}

                {scoutResults?.summary && (
                  <div className="mt-4 bg-white p-3 rounded border">
                    <h5 className="font-medium mb-2 flex items-center">
                      <Target className="h-4 w-4 mr-2 text-green-600" />
                      Enhanced Analysis Summary:
                    </h5>
                    <ul className="text-sm text-gray-600 space-y-1">
                      <li>• Sentiment: {(scoutResults.summary.positive_sentiment_ratio * 100).toFixed(1)}% positive</li>
                      <li>• Top pain points: {scoutResults.summary.top_pain_points?.join(', ') || 'None identified'}</li>
                      <li>• Active communities: {scoutResults.summary.most_active_communities?.join(', ') || 'None found'}</li>
                      <li>• Focus areas analyzed: {formData.focus_areas.join(', ')}</li>
                    </ul>
                  </div>
                )}
              </div>
            )}

            {error && (
              <div className="text-red-600 text-sm bg-red-50 p-3 rounded border border-red-200">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="h-4 w-4" />
                  <span>{error}</span>
                </div>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-6 border-t">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                disabled={isLoading}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!formData.name.trim() || isLoading}
                className="flex items-center space-x-2 px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Creating & Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" />
                    <span>Add Brand & Run Scout</span>
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