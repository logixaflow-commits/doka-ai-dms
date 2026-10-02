import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

import { Badge } from '@/components/ui/badge';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Folder, User, Shield, Plus, Trash2, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';

const API_BASE = '/api';

interface Folder {
  id: number;
  name: string;
  path: string;
  created_at: string;
}

interface Permission {
  id: number;
  user_id: number;
  folder_id: number;
  permission: 'read' | 'write' | 'admin';
  user: {
    id: number;
    username: string;
    email: string;
  };
}

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
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

const PERMISSIONS = ['read', 'write', 'admin'] as const;
const PERMISSION_LABELS = {
  read: 'Read Only',
  write: 'Read & Write',
  admin: 'Full Access'
};

const PERMISSION_COLORS = {
  read: 'bg-blue-100 text-blue-800',
  write: 'bg-amber-100 text-amber-800',
  admin: 'bg-purple-100 text-purple-800'
};

export default function FolderPermissions() {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Add permission form
  const [selectedUser, setSelectedUser] = useState<number | null>(null);
  const [selectedPermission, setSelectedPermission] = useState<'read' | 'write' | 'admin'>('read');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      
      const [foldersRes, permissionsRes, usersRes] = await Promise.all([
        apiFetch(`${API_BASE}/permissions/folders`),
        apiFetch(`${API_BASE}/permissions`),
        apiFetch(`${API_BASE}/admin/users`)
      ]);

      if (foldersRes.ok) {
        const foldersData = await foldersRes.json();
        setFolders(foldersData.folders || []);
      }

      if (permissionsRes.ok) {
        const permissionsData = await permissionsRes.json();
        setPermissions(permissionsData.permissions || []);
      }

      if (usersRes.ok) {
        const usersData = await usersRes.json();
        setUsers(usersData.users || []);
      }
    } catch (err) {
      setError('Failed to load permissions data');
      console.error('Failed to load permissions:', err);
    } finally {
      setLoading(false);
    }
  }

  async function addPermission() {
    if (!selectedFolder || !selectedUser) {
      setError('Please select a folder and user');
      return;
    }

    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/permissions`, {
        method: 'POST',
        body: JSON.stringify({
          user_id: selectedUser,
          folder_id: selectedFolder.id,
          permission: selectedPermission
        }),
      });

      if (response.ok) {
        setSuccess('Permission added successfully');
        setSelectedUser(null);
        setSelectedPermission('read');
        loadData();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to add permission');
      }
    } catch (err) {
      setError('Error adding permission');
      console.error('Failed to add permission:', err);
    }
  }

  async function removePermission(permissionId: number) {
    if (!confirm('Are you sure you want to remove this permission?')) return;

    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/permissions/${permissionId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        setSuccess('Permission removed successfully');
        loadData();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError('Failed to remove permission');
      }
    } catch (err) {
      setError('Error removing permission');
      console.error('Failed to remove permission:', err);
    }
  }

  async function updatePermission(permissionId: number, newPermission: 'read' | 'write' | 'admin') {
    try {
      setError(null);
      const response = await apiFetch(`${API_BASE}/permissions/${permissionId}`, {
        method: 'PUT',
        body: JSON.stringify({ permission: newPermission }),
      });

      if (response.ok) {
        setSuccess('Permission updated successfully');
        loadData();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError('Failed to update permission');
      }
    } catch (err) {
      setError('Error updating permission');
      console.error('Failed to update permission:', err);
    }
  }

  const folderPermissions = selectedFolder 
    ? permissions.filter(p => p.folder_id === selectedFolder.id)
    : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading permissions...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Folder Permissions</h2>
          <p className="text-slate-500 dark:text-slate-400">
            Manage folder-level access control for users
          </p>
        </div>
        <Button onClick={loadData} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-600" />
          <span className="text-red-700 dark:text-red-400">{error}</span>
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 p-4 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <span className="text-green-700 dark:text-green-400">{success}</span>
        </div>
      )}

      <Tabs defaultValue="folders" className="w-full">
        <TabsList>
          <TabsTrigger value="folders">Folders</TabsTrigger>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="add">Add Permission</TabsTrigger>
        </TabsList>

        {/* Folders Tab */}
        <TabsContent value="folders" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Folder className="w-5 h-5" />
                Folders
              </CardTitle>
              <CardDescription>
                Select a folder to view and manage permissions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {folders.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    No folders found
                  </div>
                ) : (
                  folders.map(folder => (
                    <div
                      key={folder.id}
                      className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                        selectedFolder?.id === folder.id
                          ? 'bg-blue-50 dark:bg-blue-950 border-blue-500'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-900'
                      }`}
                      onClick={() => setSelectedFolder(folder)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Folder className="w-5 h-5 text-slate-400" />
                          <div>
                            <div className="font-medium">{folder.name}</div>
                            <div className="text-sm text-slate-500">{folder.path}</div>
                          </div>
                        </div>
                        <Badge variant="outline">
                          {permissions.filter(p => p.folder_id === folder.id).length} users
                        </Badge>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Users Tab */}
        <TabsContent value="users" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                User Permissions
              </CardTitle>
              <CardDescription>
                View permissions by user
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {users.map(user => (
                  <div key={user.id} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <User className="w-5 h-5 text-slate-400" />
                        <div>
                          <div className="font-medium">{user.username}</div>
                          <div className="text-sm text-slate-500">{user.email}</div>
                        </div>
                      </div>
                      <Badge variant="outline">{user.role}</Badge>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {permissions
                        .filter(p => p.user_id === user.id)
                        .map(permission => (
                          <div
                            key={permission.id}
                            className="flex items-center gap-2 px-3 py-1 rounded-full text-sm"
                            style={{
                              backgroundColor: PERMISSION_COLORS[permission.permission].split(' ')[0],
                              color: PERMISSION_COLORS[permission.permission].split(' ')[1]
                            }}
                          >
                            <Folder className="w-3 h-3" />
                            {folders.find(f => f.id === permission.folder_id)?.name || 'Unknown'}
                            <span className="mx-1">•</span>
                            {PERMISSION_LABELS[permission.permission]}
                          </div>
                        ))}
                      {permissions.filter(p => p.user_id === user.id).length === 0 && (
                        <span className="text-sm text-slate-400">No custom permissions</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Add Permission Tab */}
        <TabsContent value="add" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Add Permission
              </CardTitle>
              <CardDescription>
                Grant folder access to users
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Folder</Label>
                  <Select value={selectedFolder?.id.toString()} onValueChange={(value) => setSelectedFolder(folders.find(f => f.id === parseInt(value)) || null)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a folder" />
                    </SelectTrigger>
                    <SelectContent>
                      {folders.map(folder => (
                        <SelectItem key={folder.id} value={folder.id.toString()}>
                          {folder.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>User</Label>
                  <Select value={selectedUser?.toString()} onValueChange={(value) => setSelectedUser(parseInt(value))}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a user" />
                    </SelectTrigger>
                    <SelectContent>
                      {users.map(user => (
                        <SelectItem key={user.id} value={user.id.toString()}>
                          {user.username} ({user.email})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Permission Level</Label>
                  <Select value={selectedPermission} onValueChange={(value: any) => setSelectedPermission(value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PERMISSIONS.map(permission => (
                        <SelectItem key={permission} value={permission}>
                          {PERMISSION_LABELS[permission]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Button onClick={addPermission} disabled={!selectedFolder || !selectedUser}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Permission
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Selected Folder Permissions */}
      {selectedFolder && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Folder className="w-5 h-5" />
              {selectedFolder.name} - Permissions
            </CardTitle>
            <CardDescription>
              Manage access for this folder
            </CardDescription>
          </CardHeader>
          <CardContent>
            {folderPermissions.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                No permissions set for this folder
              </div>
            ) : (
              <div className="space-y-3">
                {folderPermissions.map(permission => (
                  <div key={permission.id} className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900 rounded-lg">
                    <div className="flex items-center gap-3">
                      <User className="w-5 h-5 text-slate-400" />
                      <div>
                        <div className="font-medium">{permission.user.username}</div>
                        <div className="text-sm text-slate-500">{permission.user.email}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Select
                        value={permission.permission}
                        onValueChange={(value: any) => updatePermission(permission.id, value)}
                      >
                        <SelectTrigger className="w-40">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {PERMISSIONS.map(perm => (
                            <SelectItem key={perm} value={perm}>
                              {PERMISSION_LABELS[perm]}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        onClick={() => removePermission(permission.id)}
                        variant="ghost"
                        size="icon"
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
