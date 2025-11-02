import axios from 'axios';

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface ChatMessage {
  user: string;
  assistant: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_superuser: boolean;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface ChatResponse {
  response: string;
  context_used: number;
  sources: string[];
  tokens_used: number;
  cost: number;
  correlation_id: string;
}

export interface SearchResult {
  id: string;
  type: string;
  title: string;
  content: string;
  sentiment?: number;
  published_at?: string;
  campaign?: string;
  source?: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total_found: number;
  query: string;
}

export interface CampaignSummary {
  summary: string;
  metrics: {
    processed_content: number;
    insights_generated: number;
    average_sentiment: number;
  };
  tokens_used: number;
  cost: number;
}

export interface AgentStatus {
  agent_id: string;
  status: 'healthy' | 'unhealthy';
  capabilities: string[];
}

// Token management
export const tokenService = {
  getTokens(): AuthTokens | null {
    if (typeof window === 'undefined') return null;
    const access = localStorage.getItem('access_token');
    const refresh = localStorage.getItem('refresh_token');
    return access && refresh ? { access, refresh } : null;
  },

  setTokens(tokens: AuthTokens): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem('access_token', tokens.access);
    localStorage.setItem('refresh_token', tokens.refresh);
  },

  clearTokens(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  getAccessToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
  }
};

// Add token to requests
api.interceptors.request.use((config) => {
  const token = tokenService.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const tokens = tokenService.getTokens();
        if (tokens?.refresh) {
          const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
            refresh: tokens.refresh
          });
          const newTokens = { access: response.data.access, refresh: tokens.refresh };
          tokenService.setTokens(newTokens);
          original.headers.Authorization = `Bearer ${response.data.access}`;
          return api(original);
        }
      } catch (refreshError) {
        tokenService.clearTokens();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// API functions
export const apiService = {
  // Authentication
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await api.post('/auth/login/', { username, password });
    tokenService.setTokens({ access: response.data.access, refresh: response.data.refresh });
    return response.data;
  },

  async logout(): Promise<void> {
    const tokens = tokenService.getTokens();
    if (tokens?.refresh) {
      try {
        await api.post('/auth/logout/', { refresh: tokens.refresh });
      } catch (error) {
        // Continue with logout even if server request fails
      }
    }
    tokenService.clearTokens();
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get('/auth/profile/');
    return response.data;
  },

  async verifyToken(): Promise<boolean> {
    try {
      await api.get('/auth/verify-token/');
      return true;
    } catch {
      return false;
    }
  },

  // Chat with the RAG chatbot
  async chat(query: string, conversation_history: ChatMessage[] = [], campaign_id?: string): Promise<ChatResponse> {
    // Transform conversation history to backend expected format
    const formatted_history = conversation_history.flatMap(msg => [
      { role: 'user', content: msg.user },
      { role: 'assistant', content: msg.assistant }
    ]);

    const response = await api.post('/chat/', {
      query,
      conversation_history: formatted_history,
      campaign_id,
    });
    return response.data;
  },

  // Search content
  async searchContent(
    query: string,
    content_type: 'all' | 'processed' | 'insights' = 'all',
    limit: number = 20,
    campaign_id?: string
  ): Promise<SearchResponse> {
    const response = await api.post('/search/', {
      query,
      content_type,
      limit,
      campaign_id,
    });
    return response.data;
  },

  // Get campaign summary
  async getCampaignSummary(campaign_id: string): Promise<CampaignSummary> {
    const response = await api.get(`/campaigns/${campaign_id}/summary/`);
    return response.data;
  },

  // Get API root (system info)
  async getSystemInfo() {
    const response = await api.get('/');
    return response.data;
  },

  // Test connection
  async testConnection() {
    try {
      const response = await this.getSystemInfo();
      return { success: true, data: response };
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Unknown error' };
    }
  },

  // Brand management
  // Brand management - FIXED: Use consistent brand creation
  async createBrand(brandData: {
    name: string;
    description?: string;
    website?: string;
    industry?: string;
    keywords?: string[];
    scout_config?: any;  // Add scout config support
  }) {
    const response = await api.post('/brands/new/', brandData);
    return response.data;
  },

  async triggerScoutAnalysis(brandName: string, keywords: string[], brandId?: string, scoutConfig?: any) {
    const response = await api.post('/scout/analyze/', {
      brand_name: brandName,
      keywords: keywords,
      brand_id: brandId,
      scout_config: scoutConfig
    });
    return response.data;
  },

  // ADD: Get brand data
  async getBrand(brandId: string) {
    const response = await api.get(`/brands/${brandId}/`);
    return response.data;
  },

  // ADD: Update brand
  async updateBrand(brandId: string, brandData: {
    name?: string;
    description?: string;
    website?: string;
    industry?: string;
    keywords?: string[];
  }) {
    const response = await api.put(`/brands/${brandId}/`, brandData);
    return response.data;
  },

  // ADD: Update campaign
  async updateCampaign(campaignId: string, campaignData: {
    name?: string;
    description?: string;
    budget?: number;
    status?: string;
  }) {
    const response = await api.put(`/campaigns/${campaignId}/`, campaignData);
    return response.data;
  },

  // ADD: Get brands list
  async getBrands() {
    const response = await api.get('/brands/');
    return response.data;
  },

  // ADD: Get scout results for a brand
  async getScoutResults(brandId: string) {
    const response = await api.get(`/brands/${brandId}/scout-results/`);
    return response.data;
  },

  // ADD: Get communities data
  async getCommunities(brandId?: string) {
    const url = brandId ? `/communities/?brand=${brandId}` : '/communities/';
    const response = await api.get(url);
    return response.data;
  },

  // ADD: Get pain points
  async getPainPoints(brandId?: string) {
    const url = brandId ? `/pain-points/?brand=${brandId}` : '/pain-points/';
    const response = await api.get(url);
    return response.data;
  },

  // ADD: Get threads
  async getThreads(brandId?: string, communityId?: string) {
    let url = '/threads/';
    const params = new URLSearchParams();
    if (brandId) params.append('brand', brandId);
    if (communityId) params.append('community', communityId);
    if (params.toString()) url += `?${params.toString()}`;

    const response = await api.get(url);
    return response.data;
  },

  // ADD: Control brand analysis (start/stop)
  async controlBrandAnalysis(brandId: string, action: 'start' | 'stop') {
    const response = await api.post(`/brands/${brandId}/analysis/`, { action });
    return response.data;
  },

  // Campaign management with scout integration
  async createCampaign(campaignData: {
    name: string;
    description?: string;
    brand: string;
    budget?: number;
    start_date?: string;
    end_date?: string;
    keywords?: string[];
    scout_config?: any;
  }) {
    const response = await api.post('/campaigns/', campaignData);
    return response.data;
  },

  // ADD: Get campaigns
  async getCampaigns(brandId?: string) {
    const url = brandId ? `/campaigns/?brand=${brandId}` : '/campaigns/';
    const response = await api.get(url);
    return response.data;
  },

  // ADD: Get campaign details
  async getCampaign(campaignId: string) {
    const response = await api.get(`/campaigns/${campaignId}/`);
    return response.data;
  },

  // Source management
  async getSources() {
    const response = await api.get('/sources/');
    return response.data;
  },

  async createCustomSource(sourceData: {
    name: string;
    platform: string;
    url: string;
    description?: string;
    category?: string;
  }) {
    const response = await api.post('/sources/custom/', sourceData);
    return response.data;
  },

  async deleteCustomSource(sourceId: string) {
    const response = await api.delete(`/sources/custom/${sourceId}/`);
    return response.data;
  },

  // Influencer management
  async getBrandInfluencers(brandId: string, params?: { limit?: number; min_score?: number; campaign?: string }) {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.min_score !== undefined) queryParams.append('min_score', params.min_score.toString());
    if (params?.campaign) queryParams.append('campaign', params.campaign);

    const url = `/brands/${brandId}/influencers/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    const response = await api.get(url);
    return response.data;
  },

  // Enhanced Analysis - Get comprehensive analysis summary
  async getBrandAnalysisSummary(brandId: string) {
    const response = await api.get(`/brands/${brandId}/analysis-summary/`);
    return response.data;
  },

  // System Settings
  async getSystemSettings() {
    const response = await api.get('/settings/');
    return response;
  },

  async updateSystemSettings(settings: {
    custom_campaign_interval?: number;
    auto_campaign_interval?: number;
  }) {
    const response = await api.put('/settings/', settings);
    return response.data;
  }
};

export default api;