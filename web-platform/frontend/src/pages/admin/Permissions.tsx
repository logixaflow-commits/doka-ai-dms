import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import {
  Shield,
  Plus,
  Trash2,
  Key,
  Settings
} from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

const API_BASE = '/api';

interface Permission {
  id: number;
  name: string;
  description: string;
  resource: string;
  action: string;
}

interface Role {
  id: number;
  name: string;
  description: string;
  permissions: Permission[];
  is_system: boolean;
}

function getToken() {
  return localStorage.getItem('access_token');
}

async function apiFetch(url: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
}

const RESOURCES = ['documents', 'users', 'settings', 'reports', 'audit', 'system'];
const ACTIONS = ['create', 'read', 'update', 'delete', 'approve', 'export'];

export default function PermissionsPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [showRoleDialog, setShowRoleDialog] = useState(false);
  const [showPermissionDialog, setShowPermissionDialog] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    resource: '',
    action: '',
  });

  useEffect(() => {
    loadPermissions();
  }, []);

  async function loadPermissions() {
    try {
      const [rolesResp, permsResp] = await Promise.all([
        apiFetch(`${API_BASE}/admin/roles`),
        apiFetch(`${API_BASE}/admin/permissions`),
      ]);

      if (rolesResp.ok) {
        const rolesData = await rolesResp.json();
        setRoles(rolesData.roles || []);
      }

      if (permsResp.ok) {
        const permsData = await permsResp.json();
        setPermissions(permsData.permissions || []);
      }
    } catch (e) {
      console.error('Failed to load permissions:', e);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateRole(e: React.FormEvent) {
    e.preventDefault();
    try {
      const response = await apiFetch(`${API_BASE}/admin/roles`, {
        method: 'POST',
        body: JSON.stringify({
          name: formData.name,
          description: formData.description,
        }),
      });

      if (response.ok) {
        setShowRoleDialog(false);
        setFormData({ name: '', description: '', resource: '', action: '' });
        loadPermissions();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to create role');
      }
    } catch (e) {
      console.error('Failed to create role:', e);
      alert('Failed to create role');
    }
  }

  async function handleCreatePermission(e: React.FormEvent) {
    e.preventDefault();
    try {
      const response = await apiFetch(`${API_BASE}/admin/permissions`, {
        method: 'POST',
        body: JSON.stringify({
          name: `${formData.action}_${formData.resource}`,
          description: `Can ${formData.action} ${formData.resource}`,
          resource: formData.resource,
          action: formData.action,
        }),
      });

      if (response.ok) {
        setShowPermissionDialog(false);
        setFormData({ name: '', description: '', resource: '', action: '' });
        loadPermissions();
      } else {
        const error = await response.json();
        alert(error.detail || 'Failed to create permission');
      }
    } catch (e) {
      console.error('Failed to create permission:', e);
      alert('Failed to create permission');
    }
  }

  async function handleDeleteRole(roleId: number) {
    if (!confirm('Are you sure you want to delete this role?')) return;

    try {
      const response = await apiFetch(`${API_BASE}/admin/roles/${roleId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        loadPermissions();
      } else {
        alert('Failed to delete role');
      }
    } catch (e) {
      console.error('Failed to delete role:', e);
      alert('Failed to delete role');
    }
  }

  async function handleDeletePermission(permId: number) {
    if (!confirm('Are you sure you want to delete this permission?')) return;

    try {
      const response = await apiFetch(`${API_BASE}/admin/permissions/${permId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        loadPermissions();
      } else {
        alert('Failed to delete permission');
      }
    } catch (e) {
      console.error('Failed to delete permission:', e);
      alert('Failed to delete permission');
    }
  }

  async function handleTogglePermission(roleId: number, permissionId: number, currentGranted: boolean) {
    try {
      const response = await apiFetch(`${API_BASE}/admin/roles/${roleId}/permissions`, {
        method: 'PUT',
        body: JSON.stringify({
          permission_id: permissionId,
          granted: !currentGranted,
        }),
      });

      if (response.ok) {
        loadPermissions();
      } else {
        alert('Failed to update permission');
      }
    } catch (e) {
      console.error('Failed to update permission:', e);
      alert('Failed to update permission');
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Permissions & Roles</h2>
          <p className="text-slate-500 dark:text-slate-400">Manage access control and permissions</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={showPermissionDialog} onOpenChange={setShowPermissionDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Key className="w-4 h-4 mr-2" />
                Add Permission
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Permission</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreatePermission} className="space-y-4">
                <div className="space-y-2">
                  <Label>Resource</Label>
                  <Select
                    value={formData.resource}
                    onValueChange={(value) => setFormData({ ...formData, resource: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RESOURCES.map((resource) => (
                        <SelectItem key={resource} value={resource}>
                          {resource.charAt(0).toUpperCase() + resource.slice(1)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Action</Label>
                  <Select
                    value={formData.action}
                    onValueChange={(value) => setFormData({ ...formData, action: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ACTIONS.map((action) => (
                        <SelectItem key={action} value={action}>
                          {action.charAt(0).toUpperCase() + action.slice(1)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button type="submit" className="w-full">
                  Create Permission
                </Button>
              </form>
            </DialogContent>
          </Dialog>

          <Dialog open={showRoleDialog} onOpenChange={setShowRoleDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Add Role
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Role</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreateRole} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="role-name">Role Name</Label>
                  <Input
                    id="role-name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role-description">Description</Label>
                  <Input
                    id="role-description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    required
                  />
                </div>
                <Button type="submit" className="w-full">
                  Create Role
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Roles & Permissions Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Roles */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Roles
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {roles.map((role) => (
                <div key={role.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium text-slate-900 dark:text-slate-100">{role.name}</h4>
                  {role.is_system && (
                    <Badge variant="secondary" className="text-xs">System</Badge>
                  )}
                </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{role.description}</p>
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                      {role.permissions.length} permissions
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {!role.is_system && (
                      <>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteRole(role.id)}
                        >
                          <Trash2 className="w-4 h-4 text-red-500" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
              {roles.length === 0 && (
                <p className="text-center text-slate-500 dark:text-slate-400 py-4">No roles defined</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Permissions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="w-5 h-5" />
              Permissions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {permissions.map((permission) => (
                <div key={permission.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                  <div className="flex-1">
                    <h4 className="font-medium text-slate-900 dark:text-slate-100">{permission.name}</h4>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{permission.description}</p>
                    <div className="flex gap-2 mt-1">
                      <Badge variant="outline" className="text-xs">{permission.resource}</Badge>
                      <Badge variant="outline" className="text-xs">{permission.action}</Badge>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeletePermission(permission.id)}
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              ))}
              {permissions.length === 0 && (
                <p className="text-center text-slate-500 dark:text-slate-400 py-4">No permissions defined</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Role-Permission Matrix */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Role-Permission Matrix
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Permission</TableHead>
                  {roles.map((role) => (
                    <TableHead key={role.id} className="text-center">
                      {role.name}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {permissions.map((permission) => (
                  <TableRow key={permission.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{permission.name}</p>
                        <p className="text-xs text-slate-500">{permission.resource}.{permission.action}</p>
                      </div>
                    </TableCell>
                    {roles.map((role) => {
                      const hasPermission = role.permissions.some(p => p.id === permission.id);
                      return (
                        <TableCell key={role.id} className="text-center">
                          <Switch
                            checked={hasPermission}
                            onCheckedChange={() => handleTogglePermission(role.id, permission.id, hasPermission)}
                            disabled={role.is_system}
                          />
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}