import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '../components/Layout';
import { API } from '../App';
import {
  Activity,
  Users,
  Phone,
  PhoneIncoming,
  TrendingUp,
  RefreshCw,
  AlertTriangle,
  Clock,
  Edit2,
  Check,
  X,
  Loader2,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { Progress } from '../components/ui/progress';

function Dashboard() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  const [partners, setPartners] = useState([]);
  const [alerts, setAlerts] = useState({ critical: 0, high: 0, medium: 0, offline: 0 });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedPartner, setSelectedPartner] = useState('all');
  const [editingConcurrency, setEditingConcurrency] = useState(null);
  const [newConcurrencyValue, setNewConcurrencyValue] = useState('');
  const [updatingConcurrency, setUpdatingConcurrency] = useState(null);

  const fetchDashboardData = async (manual = false) => {
    try {
      if (manual) setRefreshing(true);

      const [overviewRes, partnersRes, alertsRes] = await Promise.all([
        axios.get(`${API}/dashboard/overview`),
        axios.get(`${API}/dashboard/partners`),
        axios.get(`${API}/alerts/summary`),
      ]);

      setOverview(overviewRes.data);
      setPartners(partnersRes.data);
      setAlerts(alertsRes.data);
      setLastUpdated(new Date());

      if (manual) {
        toast.success('Dashboard refreshed successfully');
      }
    } catch (error) {
      toast.error('Failed to fetch dashboard data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();

    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchDashboardData();
      }, 120000); // 2 minutes

      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getAlertClass = (alertLevel) => {
    const classes = {
      CRITICAL: 'alert-critical',
      HIGH: 'alert-high',
      MEDIUM: 'alert-medium',
      NORMAL: 'alert-normal',
      IDLE: 'alert-idle',
      ERROR: 'alert-error',
    };
    return classes[alertLevel] || '';
  };

  const getAlertBadge = (alertLevel) => {
    const badges = {
      CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
      HIGH: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      NORMAL: 'bg-green-500/20 text-green-400 border-green-500/30',
      IDLE: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      ERROR: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    };
    return badges[alertLevel] || '';
  };

  const handleUpdateConcurrency = async (partnerId, partnerName) => {
    if (!newConcurrencyValue || newConcurrencyValue < 1 || newConcurrencyValue > 100) {
      toast.error('Concurrency limit must be between 1 and 100');
      return;
    }

    setUpdatingConcurrency(partnerId);
    try {
      await axios.post(`${API}/partners/${partnerId}/concurrency`, {
        newLimit: parseInt(newConcurrencyValue),
        reason: 'Updated from dashboard'
      });
      
      toast.success(`Concurrency updated for ${partnerName}`);
      setEditingConcurrency(null);
      setNewConcurrencyValue('');
      fetchDashboardData();
    } catch (error) {
      toast.error('Failed to update concurrency');
    } finally {
      setUpdatingConcurrency(null);
    }
  };

  const filteredPartners = selectedPartner === 'all' 
    ? partners 
    : partners.filter(p => p.partner.id === selectedPartner);

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <div className="animate-pulse text-blue-400">Loading dashboard...</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="dashboard">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-bold text-white mb-1">Dashboard</h2>
            <p className="text-gray-400 text-sm">
              Last updated {formatDistanceToNow(lastUpdated, { addSuffix: true })}
            </p>
          </div>
          <Button
            onClick={() => fetchDashboardData(true)}
            disabled={refreshing}
            data-testid="refresh-dashboard-button"
            className="bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 border border-blue-500/30"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>

        {/* Alert Summary Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass rounded-xl p-4 border border-red-500/30">
            <div className="flex items-center justify-between mb-2">
              <AlertTriangle className="w-8 h-8 text-red-400" />
              <span className="text-3xl font-bold text-red-400" data-testid="critical-alerts-count">
                {alerts.critical}
              </span>
            </div>
            <p className="text-sm text-gray-400">Critical Alerts</p>
          </div>

          <div className="glass rounded-xl p-4 border border-orange-500/30">
            <div className="flex items-center justify-between mb-2">
              <AlertTriangle className="w-8 h-8 text-orange-400" />
              <span className="text-3xl font-bold text-orange-400" data-testid="high-alerts-count">
                {alerts.high}
              </span>
            </div>
            <p className="text-sm text-gray-400">High Priority</p>
          </div>

          <div className="glass rounded-xl p-4 border border-yellow-500/30">
            <div className="flex items-center justify-between mb-2">
              <AlertTriangle className="w-8 h-8 text-yellow-400" />
              <span className="text-3xl font-bold text-yellow-400" data-testid="medium-alerts-count">
                {alerts.medium}
              </span>
            </div>
            <p className="text-sm text-gray-400">Medium Priority</p>
          </div>

          <div className="glass rounded-xl p-4 border border-gray-500/30">
            <div className="flex items-center justify-between mb-2">
              <Clock className="w-8 h-8 text-gray-400" />
              <span className="text-3xl font-bold text-gray-400" data-testid="offline-partners-count">
                {alerts.offline}
              </span>
            </div>
            <p className="text-sm text-gray-400">Partners Offline</p>
          </div>
        </div>

        {/* Overview Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="glass rounded-xl p-6 border border-white/10 card-hover">
            <div className="flex items-center justify-between mb-4">
              <Activity className="w-10 h-10 text-blue-400" />
              <span className="text-4xl font-bold text-white" data-testid="campaigns-today">
                {overview?.campaignsToday || 0}
              </span>
            </div>
            <p className="text-gray-400">Campaigns Created Today</p>
          </div>

          <div className="glass rounded-xl p-6 border border-white/10 card-hover">
            <div className="flex items-center justify-between mb-4">
              <TrendingUp className="w-10 h-10 text-green-400" />
              <span className="text-4xl font-bold text-white" data-testid="running-campaigns">
                {overview?.runningCampaigns || 0}
              </span>
            </div>
            <p className="text-gray-400">Running Campaigns</p>
          </div>

          <div className="glass rounded-xl p-6 border border-white/10 card-hover">
            <div className="flex items-center justify-between mb-4">
              <Phone className="w-10 h-10 text-purple-400" />
              <span className="text-4xl font-bold text-white" data-testid="active-calls">
                {overview?.activeCalls || 0}
              </span>
            </div>
            <p className="text-gray-400">Active Calls</p>
          </div>

          <div className="glass rounded-xl p-6 border border-white/10 card-hover">
            <div className="flex items-center justify-between mb-4">
              <PhoneIncoming className="w-10 h-10 text-orange-400" />
              <span className="text-4xl font-bold text-white" data-testid="queued-calls">
                {overview?.queuedCalls || 0}
              </span>
            </div>
            <p className="text-gray-400">Queued Calls</p>
          </div>

          <div className="glass rounded-xl p-6 border border-white/10 card-hover">
            <div className="flex items-center justify-between mb-4">
              <Users className="w-10 h-10 text-pink-400" />
              <span className="text-4xl font-bold text-white" data-testid="total-partners">
                {overview?.activePartners}/{overview?.totalPartners || 0}
              </span>
            </div>
            <p className="text-gray-400">Active / Total Partners</p>
          </div>

          <div className="glass rounded-xl p-6 border border-white/10 card-hover">
            <div className="flex items-center justify-between mb-4">
              <Activity className="w-10 h-10 text-cyan-400" />
              <span className="text-4xl font-bold text-white" data-testid="avg-utilization">
                {overview?.avgUtilization?.toFixed(1) || 0}%
              </span>
            </div>
            <p className="text-gray-400">Avg Concurrency Utilization</p>
          </div>
        </div>

        {/* Partners Table */}
        <div className="glass rounded-xl border border-white/10 overflow-hidden">
          <div className="p-6 border-b border-white/10 flex items-center justify-between">
            <h3 className="text-xl font-semibold text-white">Partner Breakdown</h3>
            
            {/* Partner Filter */}
            <div className="flex items-center space-x-2">
              <label className="text-sm text-gray-400">Filter by Partner:</label>
              <select
                value={selectedPartner}
                onChange={(e) => setSelectedPartner(e.target.value)}
                className="bg-black/40 border border-white/10 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="all">All Partners</option>
                {partners.map((p) => (
                  <option key={p.partner.id} value={p.partner.id}>
                    {p.partner.partnerName}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full" data-testid="partners-table">
              <thead className="bg-white/5">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Partner</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Campaigns Today</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Running</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Active Calls</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Queued</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Concurrency</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Status</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredPartners.map((partner) => {
                  const snapshot = partner.snapshot;
                  const alertLevel = snapshot?.alertLevel || 'NORMAL';
                  const utilization = snapshot?.utilizationPercent || 0;

                  return (
                    <tr
                      key={partner.partner.id}
                      className={`${getAlertClass(alertLevel)} hover:bg-white/5 transition-colors`}
                      data-testid="partner-row"
                    >
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-semibold text-white" data-testid="partner-name">
                            {partner.partner.partnerName}
                          </p>
                          <p className="text-xs text-gray-400">Tenant {partner.partner.tenantId}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-white" data-testid="campaigns-today-cell">
                        {snapshot?.campaignsToday || 0}
                      </td>
                      <td className="px-6 py-4 text-white" data-testid="running-campaigns-cell">
                        {snapshot?.runningCampaigns || 0}
                      </td>
                      <td className="px-6 py-4 text-white" data-testid="active-calls-cell">
                        {snapshot?.activeCalls || 0}
                      </td>
                      <td className="px-6 py-4 text-white" data-testid="queued-calls-cell">
                        {snapshot?.queuedCalls || 0}
                      </td>
                      <td className="px-6 py-4" data-testid="utilization-cell">
                        <div className="space-y-2">
                          {editingConcurrency === partner.partner.id ? (
                            <div className="flex items-center space-x-2">
                              <input
                                type="number"
                                min="1"
                                max="100"
                                value={newConcurrencyValue}
                                onChange={(e) => setNewConcurrencyValue(e.target.value)}
                                className="w-20 bg-black/40 border border-white/10 text-white rounded px-2 py-1 text-sm focus:outline-none focus:border-blue-500"
                                placeholder={partner.partner.concurrencyLimit}
                                autoFocus
                              />
                              <Button
                                size="sm"
                                onClick={() => handleUpdateConcurrency(partner.partner.id, partner.partner.partnerName)}
                                className="bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/30 p-1 h-7 w-7"
                              >
                                <Check className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => {
                                  setEditingConcurrency(null);
                                  setNewConcurrencyValue('');
                                }}
                                className="bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30 p-1 h-7 w-7"
                              >
                                <X className="w-4 h-4" />
                              </Button>
                            </div>
                          ) : (
                            <div className="flex items-center space-x-2">
                              <div className="flex-1">
                                <div className="flex items-center justify-between text-sm mb-1">
                                  <span className="text-white">
                                    {snapshot?.activeCalls || 0}/{partner.partner.concurrencyLimit}
                                  </span>
                                  <span className="text-gray-400">{utilization.toFixed(1)}%</span>
                                </div>
                                <Progress value={utilization} className="h-2" />
                              </div>
                              <Button
                                size="sm"
                                onClick={() => {
                                  setEditingConcurrency(partner.partner.id);
                                  setNewConcurrencyValue(partner.partner.concurrencyLimit);
                                }}
                                className="bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 border border-purple-500/30 p-1 h-7 w-7"
                                title="Edit concurrency limit"
                              >
                                <Edit2 className="w-3 h-3" />
                              </Button>
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${getAlertBadge(
                            alertLevel
                          )}`}
                          data-testid="alert-badge"
                        >
                          {alertLevel}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <Button
                          size="sm"
                          onClick={() => navigate(`/partners/${partner.partner.id}`)}
                          data-testid="view-details-button"
                          className="bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 border border-blue-500/30"
                        >
                          View Details
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {filteredPartners.length === 0 && (
            <div className="p-12 text-center text-gray-400" data-testid="no-partners">
              <Users className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>{selectedPartner === 'all' ? 'No partners configured yet' : 'No data available for selected partner'}</p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

export default Dashboard;
