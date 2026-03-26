import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '../components/Layout';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Save, Play, RefreshCw, Loader2, Activity, Zap, Users, TrendingUp, CheckCircle2, XCircle, MinusCircle } from 'lucide-react';

const PRIORITY_META = {
  1: { label: 'P1 · Highest', color: 'text-purple-400', bg: 'bg-purple-500/20', border: 'border-purple-500/30' },
  2: { label: 'P2 · High',    color: 'text-blue-400',   bg: 'bg-blue-500/20',   border: 'border-blue-500/30'   },
  3: { label: 'P3 · Medium',  color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30' },
  4: { label: 'P4 · Low',     color: 'text-gray-400',   bg: 'bg-gray-500/20',   border: 'border-gray-500/30'   },
};

function PriorityBadge({ priority }) {
  const meta = PRIORITY_META[priority] || PRIORITY_META[4];
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${meta.bg} ${meta.color} border ${meta.border}`}>
      {meta.label}
    </span>
  );
}

function StatCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="glass rounded-xl border border-white/10 p-5 flex items-start space-x-4">
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-gray-400 text-sm">{label}</p>
        <p className="text-2xl font-bold text-white">{value ?? '—'}</p>
        {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function ConcurrencyAllocation() {
  const [settings, setSettings]           = useState(null);
  const [draftWeights, setDraftWeights]   = useState({ p1: 40, p2: 30, p3: 20, p4: 10 });
  const [draftSettings, setDraftSettings] = useState(null);
  const [partners, setPartners]           = useState([]);
  const [snapshots, setSnapshots]         = useState({});
  const [lastRun, setLastRun]             = useState(null);
  const [history, setHistory]             = useState([]);
  const [loading, setLoading]             = useState(true);
  const [savingSettings, setSavingSettings] = useState(false);
  const [triggeringRun, setTriggeringRun]   = useState(false);
  const [refreshing, setRefreshing]         = useState(false);
  const [editingMax, setEditingMax]         = useState({});   // partnerId -> draft string value
  const [savingField, setSavingField]       = useState({});   // partnerId -> 'priority'|'max'|null

  const weightSum = draftWeights.p1 + draftWeights.p2 + draftWeights.p3 + draftWeights.p4;

  const fetchAll = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const [settingsRes, partnersRes, historyRes] = await Promise.all([
        axios.get(`${API}/settings/concurrency-allocation`),
        axios.get(`${API}/partners`),
        axios.get(`${API}/concurrency/allocation-history?limit=50`),
      ]);

      const s = settingsRes.data;
      setSettings(s);
      setDraftSettings({ ...s });
      setDraftWeights({ ...s.tierWeights });

      const activePartners = partnersRes.data.filter(p => p.isActive);
      setPartners(activePartners);

      // Fetch latest snapshot for each partner
      const snapMap = {};
      await Promise.all(
        activePartners.map(async (p) => {
          try {
            const r = await axios.get(`${API}/partners/${p.id}/metrics`);
            snapMap[p.id] = r.data;
          } catch {
            snapMap[p.id] = null;
          }
        })
      );
      setSnapshots(snapMap);

      const runs = historyRes.data;
      setHistory(runs);
      if (runs.length > 0) setLastRun(runs[0]);
    } catch (error) {
      toast.error('Failed to load allocation data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    // Auto-refresh every 60s
    const interval = setInterval(() => fetchAll(true), 60000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const handleSaveSettings = async () => {
    if (weightSum !== 100) {
      toast.error('Tier weights must sum to exactly 100');
      return;
    }
    setSavingSettings(true);
    try {
      await axios.put(`${API}/settings/concurrency-allocation`, {
        globalMaxConcurrency: draftSettings.globalMaxConcurrency,
        minConcurrencyPerClient: draftSettings.minConcurrencyPerClient,
        allocationIntervalSeconds: draftSettings.allocationIntervalSeconds,
        tierWeights: draftWeights,
      });
      toast.success('Allocation settings saved');
      fetchAll(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save settings');
    } finally {
      setSavingSettings(false);
    }
  };

  const handleRunNow = async () => {
    setTriggeringRun(true);
    try {
      const res = await axios.post(`${API}/concurrency/allocate-now`);
      toast.success(`Allocation complete — ${res.data.clientsUpdated} clients updated`);
      fetchAll(true);
    } catch (error) {
      toast.error('Allocation run failed');
    } finally {
      setTriggeringRun(false);
    }
  };

  const updateClientField = async (partnerId, field, value) => {
    const parsed = field === 'maxConcurrency' ? parseInt(value) : parseInt(value);
    if (!parsed || parsed < 1) { toast.error('Value must be at least 1'); return; }

    setSavingField(prev => ({ ...prev, [partnerId]: field }));
    try {
      await axios.put(`${API}/partners/${partnerId}`, { [field]: parsed });
      toast.success(`${field === 'priority' ? 'Priority' : 'Max concurrency'} updated`);
      setEditingMax(prev => { const n = { ...prev }; delete n[partnerId]; return n; });
      fetchAll(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Update failed');
    } finally {
      setSavingField(prev => ({ ...prev, [partnerId]: null }));
    }
  };

  const formatTime = (iso) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatDate = (iso) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  // Build client rows — merge partner config + latest snapshot + last run allocation
  const lastRunAllocMap = {};
  if (lastRun?.allocations) {
    lastRun.allocations.forEach(a => { lastRunAllocMap[a.partnerId] = a; });
  }

  const clientRows = partners.map(p => {
    const snap = snapshots[p.id];
    const alloc = lastRunAllocMap[p.id];
    return {
      id: p.id,
      name: p.partnerName,
      priority: p.priority ?? 4,
      maxConcurrency: p.maxConcurrency ?? 50,
      currentLimit: p.concurrencyLimit ?? 0,
      activeCalls: snap?.activeCalls ?? 0,
      queuedCalls: snap?.queuedCalls ?? 0,
      remainingContacts: snap?.remainingCalls ?? 0,
      lastAllocated: alloc?.newLimit ?? null,
      tierPool: alloc ? Math.round(alloc.tierPool) : null,
      syncedToPartner: alloc ? alloc.syncedToPartner : null,
      syncError: alloc?.syncError ?? null,
    };
  }).sort((a, b) => a.priority - b.priority || a.name.localeCompare(b.name));

  const totalInFlight = clientRows.reduce((s, r) => s + r.activeCalls + r.queuedCalls, 0);
  const available = settings ? Math.max(0, settings.globalMaxConcurrency - totalInFlight) : 0;

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <div className="flex items-center space-x-3 text-blue-400">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Loading allocation data...</span>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold text-white">Concurrency Allocation</h2>
            <p className="text-gray-400 text-sm mt-1">
              Dynamic slot distribution across clients · auto-runs every {settings?.allocationIntervalSeconds ?? 60}s
              {lastRun && <span className="ml-2 text-gray-500">· last run {formatTime(lastRun.runAt)}</span>}
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <Button
              onClick={() => fetchAll(true)}
              disabled={refreshing}
              variant="outline"
              className="border-white/10 text-gray-300 hover:bg-white/5"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              onClick={handleRunNow}
              disabled={triggeringRun}
              className="bg-gradient-to-r from-blue-500 to-purple-600 hover:opacity-90 text-white"
            >
              {triggeringRun ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Running...</>
              ) : (
                <><Play className="w-4 h-4 mr-2" />Run Now</>
              )}
            </Button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={Zap}       label="Global Max"    value={settings?.globalMaxConcurrency} sub="Total slot ceiling"       color="bg-purple-500/20 text-purple-400" />
          <StatCard icon={Activity}  label="In-Flight"     value={totalInFlight}                   sub="Active + queued calls"    color="bg-blue-500/20 text-blue-400" />
          <StatCard icon={TrendingUp} label="Available"    value={available}                        sub="Slots free to distribute" color={available === 0 ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'} />
          <StatCard icon={Users}      label="Active Clients" value={clientRows.length}              sub="Clients in this cycle"    color="bg-yellow-500/20 text-yellow-400" />
        </div>

        {/* Last Run Status */}
        {lastRun && (
          <div className={`glass rounded-xl border p-4 flex items-center justify-between ${
            lastRun.status === 'saturated'
              ? 'border-red-500/30 bg-red-500/5'
              : lastRun.status === 'no_active_clients'
              ? 'border-gray-500/30 bg-gray-500/5'
              : 'border-green-500/30 bg-green-500/5'
          }`}>
            <div className="flex items-center space-x-3">
              <div className={`w-2 h-2 rounded-full ${
                lastRun.status === 'saturated' ? 'bg-red-400' :
                lastRun.status === 'no_active_clients' ? 'bg-gray-400' : 'bg-green-400'
              }`} />
              <div>
                <p className="text-white text-sm font-medium">
                  Last run: <span className="capitalize">{lastRun.status.replace(/_/g, ' ')}</span>
                </p>
                <p className="text-gray-400 text-xs">{formatDate(lastRun.runAt)}</p>
              </div>
            </div>
            <div className="flex items-center space-x-6 text-sm">
              <div className="text-center">
                <p className="text-white font-semibold">{lastRun.totalInFlight}</p>
                <p className="text-gray-500 text-xs">in-flight</p>
              </div>
              <div className="text-center">
                <p className="text-white font-semibold">{lastRun.availableSlots}</p>
                <p className="text-gray-500 text-xs">available</p>
              </div>
              <div className="text-center">
                <p className="text-white font-semibold">{lastRun.allocations?.length ?? 0}</p>
                <p className="text-gray-500 text-xs">clients updated</p>
              </div>
            </div>
          </div>
        )}

        {/* Settings Panel */}
        {draftSettings && (
          <div className="glass rounded-xl border border-white/10 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-white">Allocation Settings</h3>
              <Button
                onClick={handleSaveSettings}
                disabled={savingSettings || weightSum !== 100}
                className="bg-gradient-to-r from-blue-500 to-purple-600 hover:opacity-90 text-white disabled:opacity-40"
              >
                {savingSettings ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</>
                ) : (
                  <><Save className="w-4 h-4 mr-2" />Save Settings</>
                )}
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <Label className="text-gray-300">Global Max Concurrency</Label>
                <Input
                  type="number"
                  min="1"
                  value={draftSettings.globalMaxConcurrency}
                  onChange={(e) => setDraftSettings({ ...draftSettings, globalMaxConcurrency: parseInt(e.target.value) || 1 })}
                  className="bg-black/40 border-white/10 text-white"
                />
                <p className="text-xs text-gray-500">Hard ceiling across all clients</p>
              </div>

              <div className="space-y-2">
                <Label className="text-gray-300">Min Concurrency Per Client</Label>
                <Input
                  type="number"
                  min="1"
                  value={draftSettings.minConcurrencyPerClient}
                  onChange={(e) => setDraftSettings({ ...draftSettings, minConcurrencyPerClient: parseInt(e.target.value) || 1 })}
                  className="bg-black/40 border-white/10 text-white"
                />
                <p className="text-xs text-gray-500">Floor written even when demand = 0</p>
              </div>

              <div className="space-y-2">
                <Label className="text-gray-300">Allocation Interval (seconds)</Label>
                <Input
                  type="number"
                  min="10"
                  value={draftSettings.allocationIntervalSeconds}
                  onChange={(e) => setDraftSettings({ ...draftSettings, allocationIntervalSeconds: parseInt(e.target.value) || 60 })}
                  className="bg-black/40 border-white/10 text-white"
                />
                <p className="text-xs text-gray-500">How often the cycle runs (min 10s)</p>
              </div>
            </div>

            {/* Tier Weights */}
            <div className="mt-6">
              <div className="flex items-center justify-between mb-3">
                <Label className="text-gray-300 text-base">Tier Weights (%)</Label>
                <span className={`text-sm font-semibold px-2 py-0.5 rounded ${
                  weightSum === 100
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-red-500/20 text-red-400'
                }`}>
                  {weightSum}/100 {weightSum !== 100 && '· must equal 100'}
                </span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { key: 'p1', label: 'P1 · Highest', color: 'text-purple-400', ring: 'focus:ring-purple-500/40' },
                  { key: 'p2', label: 'P2 · High',    color: 'text-blue-400',   ring: 'focus:ring-blue-500/40'   },
                  { key: 'p3', label: 'P3 · Medium',  color: 'text-yellow-400', ring: 'focus:ring-yellow-500/40' },
                  { key: 'p4', label: 'P4 · Low',     color: 'text-gray-400',   ring: 'focus:ring-gray-500/40'   },
                ].map(({ key, label, color }) => (
                  <div key={key} className="space-y-2">
                    <Label className={`text-sm ${color}`}>{label}</Label>
                    <div className="relative">
                      <Input
                        type="number"
                        min="1"
                        max="97"
                        value={draftWeights[key]}
                        onChange={(e) => setDraftWeights({ ...draftWeights, [key]: parseInt(e.target.value) || 0 })}
                        className="bg-black/40 border-white/10 text-white pr-8"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">%</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Visual weight bar */}
              {weightSum === 100 && (
                <div className="mt-4 h-3 rounded-full overflow-hidden flex">
                  <div className="bg-purple-500 transition-all" style={{ width: `${draftWeights.p1}%` }} title={`P1: ${draftWeights.p1}%`} />
                  <div className="bg-blue-500 transition-all"   style={{ width: `${draftWeights.p2}%` }} title={`P2: ${draftWeights.p2}%`} />
                  <div className="bg-yellow-500 transition-all" style={{ width: `${draftWeights.p3}%` }} title={`P3: ${draftWeights.p3}%`} />
                  <div className="bg-gray-500 transition-all"   style={{ width: `${draftWeights.p4}%` }} title={`P4: ${draftWeights.p4}%`} />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Client Allocation Table */}
        <div className="glass rounded-xl border border-white/10 overflow-hidden">
          <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Client Allocations</h3>
            <p className="text-xs text-gray-500">Updated every {settings?.allocationIntervalSeconds ?? 60}s · showing latest snapshot</p>
          </div>

          {clientRows.length === 0 ? (
            <div className="p-12 text-center text-gray-400">
              No active clients found. Add partners in the Partners page first.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-white/5">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Client</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Priority</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Tier Pool</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Allocated</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Max</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Active</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Queued</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Remaining</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">DB Sync</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Utilization</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {clientRows.map((row) => {
                    const utilPct = row.currentLimit > 0 ? Math.min(100, Math.round((row.activeCalls / row.currentLimit) * 100)) : 0;
                    const utilColor = utilPct >= 80 ? 'bg-red-500' : utilPct >= 50 ? 'bg-yellow-500' : 'bg-green-500';
                    return (
                      <tr key={row.id} className="hover:bg-white/5 transition-colors">
                        <td className="px-6 py-4">
                          <p className="font-medium text-white">{row.name}</p>
                          <p className="text-xs text-gray-500">current limit: {row.currentLimit}</p>
                        </td>
                        {/* Priority — inline select */}
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-1.5">
                            <Select
                              value={String(row.priority)}
                              onValueChange={(v) => updateClientField(row.id, 'priority', v)}
                              disabled={savingField[row.id] === 'priority'}
                            >
                              <SelectTrigger className="h-7 w-36 bg-black/40 border-white/10 text-xs px-2">
                                {savingField[row.id] === 'priority'
                                  ? <Loader2 className="w-3 h-3 animate-spin text-gray-400" />
                                  : <SelectValue />
                                }
                              </SelectTrigger>
                              <SelectContent className="bg-[#1a1a2e] border-white/10 text-white text-xs">
                                <SelectItem value="1"><span className="text-purple-400">P1 · Highest</span></SelectItem>
                                <SelectItem value="2"><span className="text-blue-400">P2 · High</span></SelectItem>
                                <SelectItem value="3"><span className="text-yellow-400">P3 · Medium</span></SelectItem>
                                <SelectItem value="4"><span className="text-gray-400">P4 · Low</span></SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </td>

                        {/* Tier Pool */}
                        <td className="px-6 py-4 text-right text-gray-300 tabular-nums">
                          {row.tierPool !== null ? row.tierPool : <span className="text-gray-600">—</span>}
                        </td>

                        {/* Allocated */}
                        <td className="px-6 py-4 text-right tabular-nums">
                          {row.lastAllocated !== null ? (
                            <span className="text-white font-semibold">{row.lastAllocated}</span>
                          ) : (
                            <span className="text-gray-600">—</span>
                          )}
                        </td>

                        {/* Max Concurrency — inline edit on click */}
                        <td className="px-6 py-4 text-right">
                          {editingMax[row.id] !== undefined ? (
                            <div className="flex items-center justify-end space-x-1">
                              <Input
                                type="number"
                                min="1"
                                autoFocus
                                value={editingMax[row.id]}
                                onChange={(e) => setEditingMax(prev => ({ ...prev, [row.id]: e.target.value }))}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') updateClientField(row.id, 'maxConcurrency', editingMax[row.id]);
                                  if (e.key === 'Escape') setEditingMax(prev => { const n = { ...prev }; delete n[row.id]; return n; });
                                }}
                                onBlur={() => {
                                  if (editingMax[row.id] !== String(row.maxConcurrency)) {
                                    updateClientField(row.id, 'maxConcurrency', editingMax[row.id]);
                                  } else {
                                    setEditingMax(prev => { const n = { ...prev }; delete n[row.id]; return n; });
                                  }
                                }}
                                className="h-7 w-20 bg-black/60 border-white/20 text-white text-xs text-right px-2"
                              />
                              {savingField[row.id] === 'maxConcurrency' && <Loader2 className="w-3 h-3 animate-spin text-gray-400" />}
                            </div>
                          ) : (
                            <button
                              onClick={() => setEditingMax(prev => ({ ...prev, [row.id]: String(row.maxConcurrency) }))}
                              className="text-gray-400 hover:text-white tabular-nums text-sm px-2 py-0.5 rounded hover:bg-white/10 transition-colors"
                              title="Click to edit"
                            >
                              {row.maxConcurrency}
                            </button>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right text-blue-400 tabular-nums font-medium">{row.activeCalls}</td>
                        <td className="px-6 py-4 text-right text-yellow-400 tabular-nums font-medium">{row.queuedCalls}</td>
                        <td className="px-6 py-4 text-right text-gray-300 tabular-nums">
                          {row.remainingContacts.toLocaleString()}
                        </td>
                        <td className="px-6 py-4">
                          {row.syncedToPartner === null ? (
                            <span className="flex items-center space-x-1.5 text-gray-500">
                              <MinusCircle className="w-4 h-4" />
                              <span className="text-xs">No data</span>
                            </span>
                          ) : row.syncedToPartner ? (
                            <span className="flex items-center space-x-1.5 text-green-400">
                              <CheckCircle2 className="w-4 h-4" />
                              <span className="text-xs">Synced</span>
                            </span>
                          ) : (
                            <span className="flex items-center space-x-1.5 text-red-400" title={row.syncError ?? 'Sync failed'}>
                              <XCircle className="w-4 h-4" />
                              <span className="text-xs truncate max-w-[120px]">{row.syncError ?? 'Failed'}</span>
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-2 min-w-[100px]">
                            <div className="flex-1 bg-white/10 rounded-full h-1.5 overflow-hidden">
                              <div className={`h-full rounded-full transition-all ${utilColor}`} style={{ width: `${utilPct}%` }} />
                            </div>
                            <span className="text-xs text-gray-400 tabular-nums w-8 text-right">{utilPct}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recent Run History */}
        {history.length > 0 && (
          <div className="glass rounded-xl border border-white/10 overflow-hidden">
            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">Recent Allocation Runs</h3>
                <p className="text-xs text-gray-500 mt-0.5">Latest first · showing last {history.length} runs · all runs persisted in DB</p>
              </div>
            </div>
            {/* Fixed-height scrollable area */}
            <div className="overflow-x-auto">
              <div className="max-h-80 overflow-y-auto">
                <table className="w-full">
                  <thead className="bg-white/5 sticky top-0 z-10">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Time</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Global Max</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">In-Flight</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Available</th>
                      <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Clients</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {history.map((run, i) => (
                      <tr key={run.id ?? i} className={`hover:bg-white/5 transition-colors ${i === 0 ? 'bg-blue-500/5' : ''}`}>
                        <td className="px-6 py-3 text-sm text-gray-300">
                          {formatDate(run.runAt)}
                          {i === 0 && <span className="ml-2 text-xs text-blue-400 font-medium">latest</span>}
                        </td>
                        <td className="px-6 py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            run.status === 'saturated'
                              ? 'bg-red-500/20 text-red-400'
                              : run.status === 'no_active_clients'
                              ? 'bg-gray-500/20 text-gray-400'
                              : 'bg-green-500/20 text-green-400'
                          }`}>
                            {run.status.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-right text-gray-300 tabular-nums">{run.globalMax}</td>
                        <td className="px-6 py-3 text-right text-gray-300 tabular-nums">{run.totalInFlight}</td>
                        <td className="px-6 py-3 text-right text-gray-300 tabular-nums">{run.availableSlots}</td>
                        <td className="px-6 py-3 text-right text-gray-300 tabular-nums">{run.allocations?.length ?? 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

      </div>
    </Layout>
  );
}

export default ConcurrencyAllocation;
