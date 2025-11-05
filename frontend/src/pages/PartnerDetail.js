import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '../components/Layout';
import { API } from '../App';
import { ArrowLeft, RefreshCw, Edit, Trash2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { formatDistanceToNow } from 'date-fns';

function PartnerDetail() {
  const { partnerId } = useParams();
  const navigate = useNavigate();
  const [partner, setPartner] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [logs, setLogs] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [clearingLogs, setClearingLogs] = useState(false);

  useEffect(() => {
    fetchPartnerDetails();
  }, [partnerId]);

  const fetchPartnerDetails = async () => {
    try {
      const [partnerRes, metricsRes, logsRes, historyRes] = await Promise.all([
        axios.get(`${API}/partners/${partnerId}`),
        axios.get(`${API}/partners/${partnerId}/metrics`).catch(() => ({ data: null })),
        axios.get(`${API}/partners/${partnerId}/logs`),
        axios.get(`${API}/partners/${partnerId}/history`),
      ]);

      setPartner(partnerRes.data);
      setMetrics(metricsRes.data);
      setLogs(logsRes.data);
      setHistory(historyRes.data);
    } catch (error) {
      toast.error('Failed to fetch partner details');
      navigate('/partners');
    } finally {
      setLoading(false);
    }
  };

  const handleForceSync = async () => {
    setSyncing(true);
    try {
      await axios.post(`${API}/partners/${partnerId}/force-sync`);
      toast.success('Sync initiated');
      setTimeout(() => {
        fetchPartnerDetails();
        setSyncing(false);
      }, 2000);
    } catch (error) {
      toast.error('Failed to initiate sync');
      setSyncing(false);
    }
  };

  const handleClearLogs = async () => {
    if (!window.confirm('Are you sure you want to clear all connection logs for this partner?')) return;
    
    setClearingLogs(true);
    try {
      await axios.delete(`${API}/partners/${partnerId}/logs`);
      toast.success('Connection logs cleared');
      fetchPartnerDetails();
    } catch (error) {
      toast.error('Failed to clear logs');
    } finally {
      setClearingLogs(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <div className="animate-pulse text-blue-400">Loading partner details...</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="partner-detail">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              onClick={() => navigate('/partners')}
              variant="outline"
              data-testid="back-button"
              className="border-white/10 text-gray-300 hover:text-white"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h2 className="text-3xl font-bold text-white">{partner.partnerName}</h2>
              <p className="text-gray-400">Tenant ID: {partner.tenantId}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <Button
              onClick={handleForceSync}
              disabled={syncing}
              data-testid="force-sync-button"
              className="bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 border border-blue-500/30"
            >
              <RefreshCw className={`w-5 h-5 mr-2 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Syncing...' : 'Force Sync'}
            </Button>
            <Button
              onClick={() => navigate('/partners')}
              className="bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 border border-purple-500/30"
            >
              <Edit className="w-5 h-5 mr-2" />
              Edit
            </Button>
          </div>
        </div>

        {/* Metrics Overview */}
        {metrics && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass rounded-xl p-6 border border-white/10">
              <p className="text-gray-400 text-sm mb-2">Campaigns Today</p>
              <p className="text-4xl font-bold text-white" data-testid="campaigns-today-metric">
                {metrics.campaignsToday}
              </p>
            </div>
            <div className="glass rounded-xl p-6 border border-white/10">
              <p className="text-gray-400 text-sm mb-2">Running Campaigns</p>
              <p className="text-4xl font-bold text-white">{metrics.runningCampaigns}</p>
            </div>
            <div className="glass rounded-xl p-6 border border-white/10">
              <p className="text-gray-400 text-sm mb-2">Active Calls</p>
              <p className="text-4xl font-bold text-white">{metrics.activeCalls}</p>
            </div>
            <div className="glass rounded-xl p-6 border border-white/10">
              <p className="text-gray-400 text-sm mb-2">Queued Calls</p>
              <p className="text-4xl font-bold text-white">{metrics.queuedCalls}</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <Tabs defaultValue="metrics" className="space-y-4">
          <TabsList className="bg-white/5 border border-white/10" data-testid="partner-tabs">
            <TabsTrigger value="metrics" data-testid="metrics-tab">Current Metrics</TabsTrigger>
            <TabsTrigger value="logs" data-testid="logs-tab">Connection Logs</TabsTrigger>
            <TabsTrigger value="history" data-testid="history-tab">Concurrency History</TabsTrigger>
          </TabsList>

          <TabsContent value="metrics" data-testid="metrics-content">
            <div className="glass rounded-xl border border-white/10 p-6">
              <h3 className="text-xl font-semibold text-white mb-6">Utilization & Performance</h3>
              {metrics ? (
                <div className="space-y-6">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-gray-300">Concurrency Utilization</span>
                      <span className="text-white font-semibold">
                        {metrics.activeCalls}/{partner.concurrencyLimit} ({metrics.utilizationPercent.toFixed(1)}%)
                      </span>
                    </div>
                    <Progress value={metrics.utilizationPercent} className="h-3" />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-black/20 rounded-lg p-4">
                      <p className="text-gray-400 text-sm mb-1">Alert Level</p>
                      <p className="text-white font-semibold text-lg">{metrics.alertLevel}</p>
                    </div>
                    <div className="bg-black/20 rounded-lg p-4">
                      <p className="text-gray-400 text-sm mb-1">Last Synced</p>
                      <p className="text-white font-semibold text-lg">
                        {formatDistanceToNow(new Date(metrics.snapshotTime), { addSuffix: true })}
                      </p>
                    </div>
                  </div>

                  {metrics.alertMessage && (
                    <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                      <p className="text-yellow-400 text-sm">{metrics.alertMessage}</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-400">No metrics available yet</p>
              )}
            </div>
          </TabsContent>

          <TabsContent value="logs" data-testid="logs-content">
            <div className="glass rounded-xl border border-white/10 overflow-hidden">
              <div className="p-4 border-b border-white/10 flex justify-between items-center">
                <h3 className="text-lg font-semibold text-white">Connection Logs</h3>
                <Button
                  size="sm"
                  onClick={handleClearLogs}
                  className="bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Clear Logs
                </Button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-white/5">
                    <tr>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Timestamp</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Status</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Response Time</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Error</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {logs.map((log) => (
                      <tr key={log.id} className="hover:bg-white/5">
                        <td className="px-6 py-4 text-gray-300">
                          {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                              log.connectionStatus === 'SUCCESS'
                                ? 'bg-green-500/20 text-green-400'
                                : 'bg-red-500/20 text-red-400'
                            }`}
                          >
                            {log.connectionStatus}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-white">{log.responseTimeMs}ms</td>
                        <td className="px-6 py-4 text-gray-400 text-sm">{log.errorMessage || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {logs.length === 0 && (
                <div className="p-12 text-center text-gray-400">
                  <p>No connection logs available</p>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="history" data-testid="history-content">
            <div className="glass rounded-xl border border-white/10 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-white/5">
                    <tr>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Date</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Old Limit</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">New Limit</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Reason</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Synced</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {history.map((item) => (
                      <tr key={item.id} className="hover:bg-white/5">
                        <td className="px-6 py-4 text-gray-300">
                          {formatDistanceToNow(new Date(item.changedAt), { addSuffix: true })}
                        </td>
                        <td className="px-6 py-4 text-white">{item.oldLimit}</td>
                        <td className="px-6 py-4 text-white font-semibold">{item.newLimit}</td>
                        <td className="px-6 py-4 text-gray-400 text-sm">{item.reason || '-'}</td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                              item.syncedToPartner
                                ? 'bg-green-500/20 text-green-400'
                                : 'bg-red-500/20 text-red-400'
                            }`}
                          >
                            {item.syncedToPartner ? 'Yes' : 'Failed'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {history.length === 0 && (
                <div className="p-12 text-center text-gray-400">
                  <p>No concurrency history available</p>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}

export default PartnerDetail;
