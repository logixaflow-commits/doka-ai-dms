/**
 * Permissions JavaScript
 * Handles folder permissions management.
 */

document.addEventListener('DOMContentLoaded', () => {
    loadCurrentUser();
    loadPermissions();
    loadUsersForSelect();
    loadFoldersForSelect();
});

async function loadCurrentUser() {
    try {
        const resp = await apiFetch('/api/auth/me');
        if (resp.ok) {
            const user = await resp.json();
            document.getElementById('userName').textContent = user.username || user.full_name || 'Loading...';
            document.getElementById('userRole').textContent = user.role;
            
            // Show admin-only elements
            if (user.role === 'admin') {
                document.querySelectorAll('.admin-only').forEach(el => el.style.display = '');
            }
        }
    } catch (e) {
        console.error('Failed to load user', e);
    }
}

async function loadPermissions() {
    try {
        const roleFilter = document.getElementById('roleFilter').value;
        let url = '/api/permissions/folders';
        
        if (roleFilter) {
            url += `?role=${roleFilter}`;
        }
        
        const resp = await apiFetch(url);
        if (resp.ok) {
            const data = await resp.json();
            renderPermissionsTable(data.permissions);
            updateStats(data.permissions);
        }
    } catch (e) {
        console.error('Failed to load permissions:', e);
    }
}

function renderPermissionsTable(permissions) {
    const tbody = document.getElementById('permissionsTable');
    
    if (!permissions || permissions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="py-8 text-center text-slate-500">
                    No permissions found
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = permissions.map(perm => `
        <tr class="border-b border-slate-100 table-row-hover">
            <td class="py-3 px-4">
                <div class="font-medium text-slate-800">${perm.folder_path}</div>
            </td>
            <td class="py-3 px-4">
                ${statusBadge(perm.role)}
            </td>
            <td class="py-3 px-4">
                ${getPermissionBadge(perm.permission)}
            </td>
            <td class="py-3 px-4">
                <span class="text-sm text-slate-600">${perm.user_count} users</span>
            </td>
            <td class="py-3 px-4 text-sm text-slate-600">
                ${formatDate(perm.created_at)}
            </td>
            <td class="py-3 px-4">
                <button onclick="deletePermission(${perm.id}, '${perm.folder_path}')" 
                        class="text-red-600 hover:text-red-800 text-sm">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function updateStats(permissions) {
    document.getElementById('totalFolders').textContent = permissions.length;
    
    const activePermissions = permissions.filter(p => p.user_count > 0).length;
    document.getElementById('activePermissions').textContent = activePermissions;
    
    const totalUsers = permissions.reduce((sum, p) => sum + p.user_count, 0);
    document.getElementById('usersWithAccess').textContent = totalUsers;
}

function getPermissionBadge(permission) {
    const badges = {
        'admin': '<span class="status-badge status-approved">Admin</span>',
        'write': '<span class="status-badge status-processing">Write</span>',
        'read': '<span class="status-badge status-pending">Read</span>'
    };
    return badges[permission] || permission;
}

async function loadUsersForSelect() {
    try {
        const resp = await apiFetch('/api/admin/users');
        if (resp.ok) {
            const data = await resp.json();
            const select = document.getElementById('userSelect');
            
            data.users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = `${user.username} (${user.role})`;
                select.appendChild(option);
            });
        }
    } catch (e) {
        console.error('Failed to load users:', e);
    }
}

async function loadFoldersForSelect() {
    try {
        // Use common folder paths as defaults
        const commonFolders = [
            'Organized/Invoices',
            'Organized/BL',
            'Organized/NRC',
            'Organized/FDA',
            'Organized/Licenses',
            'Organized/Contracts',
            'Organized/Customs'
        ];
        
        const select = document.getElementById('folderSelect');
        commonFolders.forEach(folder => {
            const option = document.createElement('option');
            option.value = folder;
            option.textContent = folder;
            select.appendChild(option);
        });
    } catch (e) {
        console.error('Failed to load folders:', e);
    }
}

function openAssignModal() {
    document.getElementById('assignModal').classList.remove('hidden');
}

function closeAssignModal() {
    document.getElementById('assignModal').classList.add('hidden');
}

async function assignPermission(event) {
    event.preventDefault();
    
    const userId = parseInt(document.getElementById('userSelect').value);
    const folderPath = document.getElementById('folderSelect').value;
    const permissionLevel = document.getElementById('permissionLevel').value;
    
    if (!userId || !folderPath || !permissionLevel) {
        showToast('Please fill all fields', 'warning');
        return;
    }
    
    try {
        // First create folder permission if it doesn't exist
        const user = await (await apiFetch('/api/admin/users')).json().users.find(u => u.id === userId);
        
        const createPermResp = await apiFetch('/api/permissions/folders', {
            method: 'POST',
            body: JSON.stringify({
                folder_path: folderPath,
                role: user.role,
                permission: permissionLevel
            })
        });
        
        if (createPermResp.ok) {
            const folderPerm = await createPermResp.json();
            
            // Then assign to user
            const assignResp = await apiFetch('/api/permissions/assign', {
                method: 'POST',
                body: JSON.stringify({
                    user_id: userId,
                    permission_id: folderPerm.id
                })
            });
            
            if (assignResp.ok) {
                showToast('Permission assigned successfully', 'success');
                closeAssignModal();
                loadPermissions();
            } else {
                showToast('Failed to assign permission', 'error');
            }
        } else {
            showToast('Failed to create folder permission', 'error');
        }
    } catch (e) {
        console.error('Permission assignment error:', e);
        showToast('Failed to assign permission', 'error');
    }
}

async function deletePermission(permissionId, folderPath) {
    if (!confirm(`Remove permission for folder "${folderPath}"?`)) {
        return;
    }
    
    try {
        // Get user ID (simplified - in practice you'd need to know which user)
        // For now, we'll just show a message
        showToast('Permission removal requires user selection', 'warning');
    } catch (e) {
        console.error('Permission deletion error:', e);
        showToast('Failed to remove permission', 'error');
    }
}

async function initializeDefaults() {
    if (!confirm('Initialize default folder permissions for staff users?')) {
        return;
    }
    
    try {
        const resp = await apiFetch('/api/permissions/initialize-defaults', {
            method: 'POST'
        });
        
        if (resp.ok) {
            showToast('Default permissions initialized successfully', 'success');
            loadPermissions();
        } else {
            showToast('Failed to initialize defaults', 'error');
        }
    } catch (e) {
        console.error('Initialization error:', e);
        showToast('Failed to initialize defaults', 'error');
    }
}