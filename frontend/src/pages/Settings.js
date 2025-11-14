import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '../components/Layout';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Save, Lock, Loader2 } from 'lucide-react';

function Settings() {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API}/settings`);
      const settingsObj = {};
      response.data.forEach((setting) => {
        settingsObj[setting.settingKey] = setting.settingValue;
      });
      setSettings(settingsObj);
    } catch (error) {
      toast.error('Failed to fetch settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const settingsArray = Object.keys(settings).map((key) => ({
        settingKey: key,
        settingValue: settings[key],
      }));

      await axios.put(`${API}/settings`, settingsArray);
      toast.success('Settings saved successfully');
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const updateSetting = (key, value) => {
    setSettings({ ...settings, [key]: value });
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    
    // Validation
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }

    if (passwordData.newPassword.length < 8) {
      toast.error('Password must be at least 8 characters long');
      return;
    }

    setChangingPassword(true);
    try {
      await axios.post(`${API}/auth/change-password`, {
        currentPassword: passwordData.currentPassword,
        newPassword: passwordData.newPassword
      });
      
      toast.success('Password changed successfully');
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setChangingPassword(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <div className="animate-pulse text-blue-400">Loading settings...</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="settings-page">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold text-white">Settings</h2>
          <Button
            onClick={handleSave}
            disabled={saving}
            data-testid="save-settings-button"
            className="bg-gradient-to-r from-blue-500 to-purple-600 hover:opacity-90 text-white"
          >
            <Save className="w-5 h-5 mr-2" />
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>

        {/* Change Password Section */}
        <div className="glass rounded-xl border border-white/10 p-6">
          <h3 className="text-xl font-semibold text-white mb-6 flex items-center">
            <Lock className="w-5 h-5 mr-2" />
            Change Password
          </h3>
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
            <div className="space-y-2">
              <Label className="text-gray-300">Current Password</Label>
              <Input
                type="password"
                value={passwordData.currentPassword}
                onChange={(e) => setPasswordData({...passwordData, currentPassword: e.target.value})}
                required
                className="bg-black/40 border-white/10 text-white"
                placeholder="Enter current password"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-gray-300">New Password</Label>
              <Input
                type="password"
                value={passwordData.newPassword}
                onChange={(e) => setPasswordData({...passwordData, newPassword: e.target.value})}
                required
                minLength={8}
                className="bg-black/40 border-white/10 text-white"
                placeholder="Enter new password (min 8 characters)"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-gray-300">Confirm New Password</Label>
              <Input
                type="password"
                value={passwordData.confirmPassword}
                onChange={(e) => setPasswordData({...passwordData, confirmPassword: e.target.value})}
                required
                className="bg-black/40 border-white/10 text-white"
                placeholder="Confirm new password"
              />
            </div>

            <Button
              type="submit"
              disabled={changingPassword}
              className="bg-gradient-to-r from-blue-500 to-purple-600 hover:opacity-90 text-white"
            >
              {changingPassword ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Changing Password...
                </>
              ) : (
                <>
                  <Lock className="w-4 h-4 mr-2" />
                  Change Password
                </>
              )}
            </Button>
          </form>
        </div>

        {/* Dashboard Refresh Settings */}
        <div className="glass rounded-xl border border-white/10 p-6">
          <h3 className="text-xl font-semibold text-white mb-6">Dashboard Refresh Configuration</h3>
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-gray-300 text-base">Enable Auto-Refresh</Label>
                <p className="text-sm text-gray-400 mt-1">Automatically refresh dashboard data</p>
              </div>
              <Switch
                checked={settings.autoRefreshEnabled || false}
                onCheckedChange={(checked) => updateSetting('autoRefreshEnabled', checked)}
                data-testid="auto-refresh-toggle"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-gray-300">Refresh Interval (seconds)</Label>
              <Input
                type="number"
                value={settings.refreshInterval || 120}
                onChange={(e) => updateSetting('refreshInterval', parseInt(e.target.value))}
                min="30"
                max="900"
                data-testid="refresh-interval-input"
                className="bg-black/40 border-white/10 text-white"
              />
              <p className="text-xs text-gray-400">Range: 30-900 seconds (0.5-15 minutes)</p>
            </div>

            <div className="space-y-2">
              <Label className="text-gray-300">Query Timeout (seconds)</Label>
              <Input
                type="number"
                value={settings.queryTimeout || 60}
                onChange={(e) => updateSetting('queryTimeout', parseInt(e.target.value))}
                min="10"
                max="180"
                className="bg-black/40 border-white/10 text-white"
              />
              <p className="text-xs text-gray-400">Range: 10-180 seconds</p>
            </div>

            <div className="space-y-2">
              <Label className="text-gray-300">Connection Timeout (seconds)</Label>
              <Input
                type="number"
                value={settings.connectionTimeout || 30}
                onChange={(e) => updateSetting('connectionTimeout', parseInt(e.target.value))}
                min="10"
                max="120"
                className="bg-black/40 border-white/10 text-white"
              />
              <p className="text-xs text-gray-400">Range: 10-120 seconds</p>
            </div>

            <div className="space-y-2">
              <Label className="text-gray-300">Concurrent Partner Query Limit</Label>
              <Input
                type="number"
                value={settings.concurrentPartnerLimit || 5}
                onChange={(e) => updateSetting('concurrentPartnerLimit', parseInt(e.target.value))}
                min="1"
                max="20"
                className="bg-black/40 border-white/10 text-white"
              />
              <p className="text-xs text-gray-400">Range: 1-20 partners</p>
            </div>
          </div>
        </div>

        {/* Alert Thresholds */}
        <div className="glass rounded-xl border border-white/10 p-6">
          <h3 className="text-xl font-semibold text-white mb-6">Alert Thresholds Configuration</h3>
          <div className="space-y-6">
            <div>
              <h4 className="text-lg font-medium text-red-400 mb-4">Critical Alert Thresholds</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-gray-300">Queued Calls Greater Than</Label>
                  <Input
                    type="number"
                    value={settings.criticalQueuedThreshold || 200}
                    onChange={(e) => updateSetting('criticalQueuedThreshold', parseInt(e.target.value))}
                    className="bg-black/40 border-white/10 text-white"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-300">Utilization Less Than (%)</Label>
                  <Input
                    type="number"
                    value={settings.criticalUtilizationThreshold || 30}
                    onChange={(e) => updateSetting('criticalUtilizationThreshold', parseInt(e.target.value))}
                    className="bg-black/40 border-white/10 text-white"
                  />
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-lg font-medium text-orange-400 mb-4">High Priority Alert Thresholds</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-gray-300">Queued Calls Min</Label>
                  <Input
                    type="number"
                    value={settings.highQueuedMin || 100}
                    onChange={(e) => updateSetting('highQueuedMin', parseInt(e.target.value))}
                    className="bg-black/40 border-white/10 text-white"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-gray-300">Queued Calls Max</Label>
                  <Input
                    type="number"
                    value={settings.highQueuedMax || 200}
                    onChange={(e) => updateSetting('highQueuedMax', parseInt(e.target.value))}
                    className="bg-black/40 border-white/10 text-white"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Email Notification Settings */}
        <div className="glass rounded-xl border border-white/10 p-6">
          <h3 className="text-xl font-semibold text-white mb-6">Email Notification Settings</h3>
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-gray-300 text-base">Enable Email Alerts</Label>
                <p className="text-sm text-gray-400 mt-1">Send email notifications for critical alerts</p>
              </div>
              <Switch
                checked={settings.emailAlertsEnabled || false}
                onCheckedChange={(checked) => updateSetting('emailAlertsEnabled', checked)}
              />
            </div>

            {settings.emailAlertsEnabled && (
              <div className="space-y-4 p-4 bg-black/20 rounded-lg border border-white/10">
                <div className="space-y-2">
                  <Label className="text-gray-300">Recipient Emails (comma-separated)</Label>
                  <Input
                    value={settings.emailRecipients || 'admin@jobtalk.com'}
                    onChange={(e) => updateSetting('emailRecipients', e.target.value)}
                    placeholder="email1@example.com, email2@example.com"
                    className="bg-black/40 border-white/10 text-white"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Public API CORS Configuration */}
        <div className="glass rounded-xl border border-white/10 p-6">
          <h3 className="text-xl font-semibold text-white mb-6">Public API CORS Configuration</h3>
          <div className="space-y-6">
            <div className="space-y-2">
              <Label className="text-gray-300 text-base">Allowed Domains for Public API</Label>
              <p className="text-sm text-gray-400 mt-1">
                Configure which domains can access the public statistics API endpoint (/api/public/stats).
                Leave empty to allow all origins.
              </p>
              <Input
                value={settings.publicApiAllowedDomains || ''}
                onChange={(e) => updateSetting('publicApiAllowedDomains', e.target.value)}
                placeholder="https://example.com,https://www.example.com,https://another-site.com"
                className="bg-black/40 border-white/10 text-white"
              />
              <p className="text-xs text-gray-400">
                Format: Comma-separated list of domains with protocol (e.g., https://example.com)
              </p>
            </div>

            <div className="p-4 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <h4 className="text-sm font-semibold text-blue-400 mb-2">ℹ️ How to use:</h4>
              <ul className="text-xs text-gray-300 space-y-1 list-disc list-inside">
                <li><strong>Empty value:</strong> Allows requests from any domain (less secure)</li>
                <li><strong>With domains:</strong> Only listed domains can access the public API</li>
                <li><strong>Example:</strong> https://mywebsite.com,https://www.mywebsite.com</li>
              </ul>
            </div>

            <div className="p-4 bg-green-500/10 rounded-lg border border-green-500/20">
              <h4 className="text-sm font-semibold text-green-400 mb-2">📊 Public API Endpoint:</h4>
              <div className="space-y-2">
                <code className="text-xs text-gray-300 block bg-black/40 p-2 rounded">
                  GET /api/public/stats
                </code>
                <p className="text-xs text-gray-400">
                  This endpoint provides call and submittal statistics for external websites. 
                  No authentication required.
                </p>
                <a 
                  href="/app/PUBLIC_API_DOCUMENTATION.md" 
                  target="_blank"
                  className="text-xs text-blue-400 hover:underline inline-block"
                >
                  View complete documentation →
                </a>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            onClick={handleSave}
            disabled={saving}
            data-testid="save-settings-button-bottom"
            className="bg-gradient-to-r from-blue-500 to-purple-600 hover:opacity-90 text-white"
          >
            <Save className="w-5 h-5 mr-2" />
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        </div>
      </div>
    </Layout>
  );
}

export default Settings;
