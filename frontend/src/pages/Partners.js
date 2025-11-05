import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '../components/Layout';
import { API } from '../App';
import { Plus, Edit, Trash2, TestTube, Eye } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Textarea } from '../components/ui/textarea';
import { useNavigate } from 'react-router-dom';

function Partners() {
  const navigate = useNavigate();
  const [partners, setPartners] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPartner, setEditingPartner] = useState(null);
  const [formData, setFormData] = useState({
    partnerName: '',
    tenantId: '',
    dbHost: '',
    dbPort: 3306,
    dbName: '',
    dbUsername: '',
    dbPassword: '',
    concurrencyLimit: 10,
    isActive: true,
    sshConfig: {
      enabled: true,
      host: '',
      port: 22,
      username: '',
      password: '',
      privateKey: '',
      passphrase: '',
    },
  });

  useEffect(() => {
    fetchPartners();
  }, []);

  const fetchPartners = async () => {
    try {
      const response = await axios.get(`${API}/partners`);
      setPartners(response.data);
    } catch (error) {
      toast.error('Failed to fetch partners');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate SSH configuration if enabled (only for new partners)
    if (formData.sshConfig.enabled && !editingPartner) {
      const hasPassword = formData.sshConfig.password && formData.sshConfig.password.trim() !== '';
      const hasPrivateKey = formData.sshConfig.privateKey && formData.sshConfig.privateKey.trim() !== '';
      
      if (!hasPassword && !hasPrivateKey) {
        toast.error('Please provide either SSH Password or SSH Private Key');
        return;
      }
    }

    try {
      // Prepare data - only include sensitive SSH fields if they have values
      const submitData = { ...formData };
      
      if (editingPartner) {
        // When editing, only include SSH sensitive fields if user entered new values
        if (!submitData.sshConfig.password || submitData.sshConfig.password === '') {
          delete submitData.sshConfig.password;
        }
        if (!submitData.sshConfig.privateKey || submitData.sshConfig.privateKey === '') {
          delete submitData.sshConfig.privateKey;
        }
        if (!submitData.sshConfig.passphrase || submitData.sshConfig.passphrase === '') {
          delete submitData.sshConfig.passphrase;
        }
      }
      
      if (editingPartner) {
        await axios.put(`${API}/partners/${editingPartner.id}`, submitData);
        toast.success('Partner updated successfully');
      } else {
        await axios.post(`${API}/partners`, submitData);
        toast.success('Partner created successfully');
      }

      fetchPartners();
      setDialogOpen(false);
      resetForm();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this partner?')) return;

    try {
      await axios.delete(`${API}/partners/${id}`);
      toast.success('Partner deleted successfully');
      fetchPartners();
    } catch (error) {
      toast.error('Failed to delete partner');
    }
  };

  const handleTest = async (id) => {
    const loadingToast = toast.loading('Testing connection...');
    try {
      const response = await axios.post(`${API}/partners/${id}/test`);
      toast.dismiss(loadingToast);
      if (response.data.success) {
        toast.success(`Connection successful (${response.data.responseTimeMs}ms)`);
      } else {
        toast.error(response.data.message);
      }
    } catch (error) {
      toast.dismiss(loadingToast);
      toast.error('Connection test failed');
    }
  };

  const resetForm = () => {
    setFormData({
      partnerName: '',
      tenantId: '',
      dbHost: '',
      dbPort: 3306,
      dbName: '',
      dbUsername: '',
      dbPassword: '',
      concurrencyLimit: 10,
      isActive: true,
      sshConfig: {
        enabled: true,
        host: '',
        port: 22,
        username: '',
        password: '',
        privateKey: '',
        passphrase: '',
      },
    });
    setEditingPartner(null);
  };

  const openEditDialog = (partner) => {
    setEditingPartner(partner);
    setFormData({
      partnerName: partner.partnerName,
      tenantId: partner.tenantId,
      dbHost: partner.dbHost,
      dbPort: partner.dbPort,
      dbName: partner.dbName,
      dbUsername: partner.dbUsername,
      dbPassword: '', // Don't show encrypted password
      concurrencyLimit: partner.concurrencyLimit,
      isActive: partner.isActive,
      sshConfig: {
        ...partner.sshConfig,
        password: '', // Don't show encrypted password
        privateKey: '', // Don't show encrypted key
        passphrase: '', // Don't show encrypted passphrase
      },
    });
    setDialogOpen(true);
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="partners-page">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold text-white">Partners Management</h2>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button
                onClick={resetForm}
                data-testid="add-partner-button"
                className="bg-gradient-to-r from-blue-500 to-purple-600 hover:opacity-90 text-white"
              >
                <Plus className="w-5 h-5 mr-2" />
                Add Partner
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto bg-[#1a1a2e] border-white/10">
              <DialogHeader>
                <DialogTitle className="text-white">
                  {editingPartner ? 'Edit Partner' : 'Add New Partner'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-6" data-testid="partner-form">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-gray-300">Partner Name *</Label>
                    <Input
                      value={formData.partnerName}
                      onChange={(e) => setFormData({ ...formData, partnerName: e.target.value })}
                      required
                      className="bg-black/40 border-white/10 text-white"
                      data-testid="partner-name-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-gray-300">Tenant ID *</Label>
                    <Input
                      type="number"
                      value={formData.tenantId}
                      onChange={(e) => setFormData({ ...formData, tenantId: e.target.value })}
                      required
                      className="bg-black/40 border-white/10 text-white"
                      data-testid="tenant-id-input"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-gray-300">Database Host *</Label>
                    <Input
                      value={formData.dbHost}
                      onChange={(e) => setFormData({ ...formData, dbHost: e.target.value })}
                      required
                      className="bg-black/40 border-white/10 text-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-gray-300">Database Port</Label>
                    <Input
                      type="number"
                      value={formData.dbPort}
                      onChange={(e) => setFormData({ ...formData, dbPort: e.target.value })}
                      className="bg-black/40 border-white/10 text-white"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-gray-300">Database Name *</Label>
                    <Input
                      value={formData.dbName}
                      onChange={(e) => setFormData({ ...formData, dbName: e.target.value })}
                      required
                      className="bg-black/40 border-white/10 text-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-gray-300">Database Username *</Label>
                    <Input
                      value={formData.dbUsername}
                      onChange={(e) => setFormData({ ...formData, dbUsername: e.target.value })}
                      required
                      className="bg-black/40 border-white/10 text-white"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-gray-300">Database Password {editingPartner && '(leave blank to keep current)'}</Label>
                  <Input
                    type="password"
                    value={formData.dbPassword}
                    onChange={(e) => setFormData({ ...formData, dbPassword: e.target.value })}
                    required={!editingPartner}
                    className="bg-black/40 border-white/10 text-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-gray-300">Concurrency Limit</Label>
                  <Input
                    type="number"
                    min="1"
                    max="100"
                    value={formData.concurrencyLimit}
                    onChange={(e) => setFormData({ ...formData, concurrencyLimit: e.target.value })}
                    className="bg-black/40 border-white/10 text-white"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    checked={formData.sshConfig.enabled}
                    onCheckedChange={(checked) =>
                      setFormData({ ...formData, sshConfig: { ...formData.sshConfig, enabled: checked } })
                    }
                  />
                  <Label className="text-gray-300">Enable SSH Tunnel</Label>
                </div>

                {formData.sshConfig.enabled && (
                  <div className="space-y-4 p-4 bg-black/20 rounded-lg border border-white/10">
                    <h4 className="text-white font-semibold">SSH Configuration</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label className="text-gray-300">SSH Host *</Label>
                        <Input
                          value={formData.sshConfig.host}
                          onChange={(e) =>
                            setFormData({ ...formData, sshConfig: { ...formData.sshConfig, host: e.target.value } })
                          }
                          required
                          className="bg-black/40 border-white/10 text-white"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label className="text-gray-300">SSH Port</Label>
                        <Input
                          type="number"
                          value={formData.sshConfig.port}
                          onChange={(e) =>
                            setFormData({ ...formData, sshConfig: { ...formData.sshConfig, port: e.target.value } })
                          }
                          className="bg-black/40 border-white/10 text-white"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-gray-300">SSH Username *</Label>
                      <Input
                        value={formData.sshConfig.username}
                        onChange={(e) =>
                          setFormData({ ...formData, sshConfig: { ...formData.sshConfig, username: e.target.value } })
                        }
                        required
                        className="bg-black/40 border-white/10 text-white"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="text-gray-300">
                        SSH Password {editingPartner && '(leave blank to keep current)'}
                      </Label>
                      <Input
                        type="password"
                        value={formData.sshConfig.password}
                        onChange={(e) =>
                          setFormData({ ...formData, sshConfig: { ...formData.sshConfig, password: e.target.value } })
                        }
                        className="bg-black/40 border-white/10 text-white"
                        placeholder={editingPartner ? "Enter new password to update" : "Enter SSH password"}
                      />
                      <p className="text-xs text-gray-400">Primary authentication method</p>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-gray-300">
                        SSH Private Key (optional) {editingPartner && '(leave blank to keep current)'}
                      </Label>
                      <Textarea
                        value={formData.sshConfig.privateKey}
                        onChange={(e) =>
                          setFormData({ ...formData, sshConfig: { ...formData.sshConfig, privateKey: e.target.value } })
                        }
                        rows={4}
                        className="bg-black/40 border-white/10 text-white font-mono text-xs"
                        placeholder={editingPartner ? "Enter new private key to update" : "-----BEGIN RSA PRIVATE KEY-----"}
                      />
                      <p className="text-xs text-gray-400">Alternative to password authentication</p>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-gray-300">
                        SSH Passphrase (if key is encrypted) {editingPartner && '(leave blank to keep current)'}
                      </Label>
                      <Input
                        type="password"
                        value={formData.sshConfig.passphrase}
                        onChange={(e) =>
                          setFormData({ ...formData, sshConfig: { ...formData.sshConfig, passphrase: e.target.value } })
                        }
                        className="bg-black/40 border-white/10 text-white"
                        placeholder={editingPartner ? "Enter new passphrase to update" : "Enter passphrase if key is encrypted"}
                      />
                    </div>
                  </div>
                )}

                <div className="flex items-center space-x-2">
                  <Switch checked={formData.isActive} onCheckedChange={(checked) => setFormData({ ...formData, isActive: checked })} />
                  <Label className="text-gray-300">Active</Label>
                </div>

                <div className="flex justify-end space-x-3">
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    data-testid="submit-partner-button"
                    className="bg-gradient-to-r from-blue-500 to-purple-600 text-white"
                  >
                    {editingPartner ? 'Update' : 'Create'} Partner
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <div className="glass rounded-xl border border-white/10 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full" data-testid="partners-list-table">
              <thead className="bg-white/5">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Partner Name</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Tenant ID</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Database</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Concurrency</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Status</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {partners.map((partner) => (
                  <tr key={partner.id} className="hover:bg-white/5 transition-colors" data-testid="partner-list-row">
                    <td className="px-6 py-4">
                      <p className="font-semibold text-white">{partner.partnerName}</p>
                    </td>
                    <td className="px-6 py-4 text-white">{partner.tenantId}</td>
                    <td className="px-6 py-4">
                      <p className="text-white text-sm">{partner.dbHost}</p>
                      <p className="text-gray-400 text-xs">{partner.dbName}</p>
                    </td>
                    <td className="px-6 py-4 text-white">{partner.concurrencyLimit}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                          partner.isActive
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                            : 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
                        }`}
                      >
                        {partner.isActive ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <Button
                          size="sm"
                          onClick={() => navigate(`/partners/${partner.id}`)}
                          data-testid="view-partner-button"
                          className="bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 border border-blue-500/30"
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleTest(partner.id)}
                          data-testid="test-connection-button"
                          className="bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/30"
                        >
                          <TestTube className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => openEditDialog(partner)}
                          data-testid="edit-partner-button"
                          className="bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 border border-yellow-500/30"
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleDelete(partner.id)}
                          data-testid="delete-partner-button"
                          className="bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {partners.length === 0 && (
            <div className="p-12 text-center text-gray-400" data-testid="no-partners-message">
              <p>No partners configured yet. Click "Add Partner" to get started.</p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

export default Partners;
