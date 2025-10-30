'use client';

import { useState, useEffect } from 'react';
import { Settings, Save, Clock, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { apiService } from '@/lib/api';

interface CampaignSettings {
  custom_campaign_interval: number;  // in seconds
  auto_campaign_interval: number;    // in seconds
}

export default function SettingsManager() {
  const [settings, setSettings] = useState<CampaignSettings>({
    custom_campaign_interval: 3600,  // Default 1 hour
    auto_campaign_interval: 3600,    // Default 1 hour
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await apiService.getSystemSettings();
      if (response.data) {
        setSettings({
          custom_campaign_interval: response.data.custom_campaign_interval || 3600,
          auto_campaign_interval: response.data.auto_campaign_interval || 3600,
        });
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error);
      // Use defaults if fetch fails
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage(null);

      await apiService.updateSystemSettings(settings);

      setMessage({
        type: 'success',
        text: 'Settings saved successfully! New campaigns will use these intervals.'
      });

      // Clear message after 3 seconds
      setTimeout(() => setMessage(null), 3000);
    } catch (error: any) {
      console.error('Failed to save settings:', error);
      setMessage({
        type: 'error',
        text: error.response?.data?.error || 'Failed to save settings. Please try again.'
      });
    } finally {
      setSaving(false);
    }
  };

  const convertSecondsToTime = (seconds: number): { hours: number, minutes: number } => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return { hours, minutes };
  };

  const convertTimeToSeconds = (hours: number, minutes: number): number => {
    return (hours * 3600) + (minutes * 60);
  };

  const handleIntervalChange = (type: 'custom' | 'auto', hours: number, minutes: number) => {
    const seconds = convertTimeToSeconds(hours, minutes);
    if (type === 'custom') {
      setSettings({ ...settings, custom_campaign_interval: seconds });
    } else {
      setSettings({ ...settings, auto_campaign_interval: seconds });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading settings...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 flex items-center">
          <Settings className="h-5 w-5 mr-2" />
          Campaign Schedule Settings
        </h2>
        <p className="mt-1 text-sm text-gray-600">
          Configure the default scheduling intervals for campaigns. These settings will apply to newly created campaigns.
        </p>
      </div>

      {/* Settings Form */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Custom Campaign Settings */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center mb-4">
            <div className="bg-green-100 p-2 rounded-lg">
              <Clock className="h-5 w-5 text-green-600" />
            </div>
            <div className="ml-3">
              <h3 className="text-lg font-medium text-gray-900">Custom Campaigns</h3>
              <p className="text-sm text-gray-500">User-created campaigns</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Schedule Interval
              </label>
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    value={convertSecondsToTime(settings.custom_campaign_interval).hours}
                    onChange={(e) => {
                      const time = convertSecondsToTime(settings.custom_campaign_interval);
                      handleIntervalChange('custom', parseInt(e.target.value) || 0, time.minutes);
                    }}
                    className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                  <span className="text-sm text-gray-600">hours</span>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    min="0"
                    max="59"
                    value={convertSecondsToTime(settings.custom_campaign_interval).minutes}
                    onChange={(e) => {
                      const time = convertSecondsToTime(settings.custom_campaign_interval);
                      handleIntervalChange('custom', time.hours, parseInt(e.target.value) || 0);
                    }}
                    className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                  <span className="text-sm text-gray-600">minutes</span>
                </div>
              </div>
              <p className="mt-2 text-xs text-gray-500">
                Default: 1 hour. Minimum: 1 minute. Examples: 10 minutes, 1 hour 30 minutes
              </p>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-md p-3">
              <p className="text-xs text-green-800">
                <strong>Current setting:</strong> Run every {convertSecondsToTime(settings.custom_campaign_interval).hours > 0 && `${convertSecondsToTime(settings.custom_campaign_interval).hours} hour${convertSecondsToTime(settings.custom_campaign_interval).hours !== 1 ? 's' : ''}`}{convertSecondsToTime(settings.custom_campaign_interval).hours > 0 && convertSecondsToTime(settings.custom_campaign_interval).minutes > 0 && ' '}{convertSecondsToTime(settings.custom_campaign_interval).minutes > 0 && `${convertSecondsToTime(settings.custom_campaign_interval).minutes} minute${convertSecondsToTime(settings.custom_campaign_interval).minutes !== 1 ? 's' : ''}`}
              </p>
              <p className="text-xs text-green-700 mt-1">
                ({settings.custom_campaign_interval} seconds)
              </p>
            </div>
          </div>
        </div>

        {/* Automatic Campaign Settings */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center mb-4">
            <div className="bg-orange-100 p-2 rounded-lg">
              <Clock className="h-5 w-5 text-orange-600" />
            </div>
            <div className="ml-3">
              <h3 className="text-lg font-medium text-gray-900">Automatic Campaigns</h3>
              <p className="text-sm text-gray-500">Brand Analytics campaigns</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Schedule Interval
              </label>
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    value={convertSecondsToTime(settings.auto_campaign_interval).hours}
                    onChange={(e) => {
                      const time = convertSecondsToTime(settings.auto_campaign_interval);
                      handleIntervalChange('auto', parseInt(e.target.value) || 0, time.minutes);
                    }}
                    className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  />
                  <span className="text-sm text-gray-600">hours</span>
                </div>
                <div className="flex items-center space-x-2">
                  <input
                    type="number"
                    min="0"
                    max="59"
                    value={convertSecondsToTime(settings.auto_campaign_interval).minutes}
                    onChange={(e) => {
                      const time = convertSecondsToTime(settings.auto_campaign_interval);
                      handleIntervalChange('auto', time.hours, parseInt(e.target.value) || 0);
                    }}
                    className="w-20 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  />
                  <span className="text-sm text-gray-600">minutes</span>
                </div>
              </div>
              <p className="mt-2 text-xs text-gray-500">
                Default: 1 hour. Minimum: 1 minute. Examples: 10 minutes, 1 hour 30 minutes
              </p>
            </div>

            <div className="bg-orange-50 border border-orange-200 rounded-md p-3">
              <p className="text-xs text-orange-800">
                <strong>Current setting:</strong> Run every {convertSecondsToTime(settings.auto_campaign_interval).hours > 0 && `${convertSecondsToTime(settings.auto_campaign_interval).hours} hour${convertSecondsToTime(settings.auto_campaign_interval).hours !== 1 ? 's' : ''}`}{convertSecondsToTime(settings.auto_campaign_interval).hours > 0 && convertSecondsToTime(settings.auto_campaign_interval).minutes > 0 && ' '}{convertSecondsToTime(settings.auto_campaign_interval).minutes > 0 && `${convertSecondsToTime(settings.auto_campaign_interval).minutes} minute${convertSecondsToTime(settings.auto_campaign_interval).minutes !== 1 ? 's' : ''}`}
              </p>
              <p className="text-xs text-orange-700 mt-1">
                ({settings.auto_campaign_interval} seconds)
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Important Notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <AlertCircle className="h-5 w-5 text-blue-400 mt-0.5" />
          <div className="ml-3">
            <h4 className="text-sm font-medium text-blue-800">Important Notes</h4>
            <ul className="mt-2 text-sm text-blue-700 space-y-1 list-disc list-inside">
              <li>These settings apply only to <strong>newly created</strong> campaigns</li>
              <li>Existing campaigns will keep their current schedule intervals</li>
              <li>You can edit individual campaign schedules from the Campaigns tab</li>
              <li>Very frequent intervals (e.g., every 1-10 minutes) may significantly increase API costs</li>
              <li>Recommended minimum for production: 10-15 minutes to avoid rate limiting</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200">
        <div className="flex-1">
          {message && (
            <div className={`flex items-center space-x-2 ${
              message.type === 'success' ? 'text-green-600' : 'text-red-600'
            }`}>
              {message.type === 'success' ? (
                <CheckCircle className="h-5 w-5" />
              ) : (
                <AlertCircle className="h-5 w-5" />
              )}
              <span className="text-sm font-medium">{message.text}</span>
            </div>
          )}
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center space-x-2 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Saving...</span>
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              <span>Save Settings</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
