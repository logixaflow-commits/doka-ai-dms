/**
 * Enterprise DMS - Common JavaScript Utilities
 * Shared functions used across multiple templates
 */

// API Configuration
const API_BASE = window.location.origin + '/api';

// Token Management
function getToken() {
    return localStorage.getItem('access_token');
}

function setToken(token) {
    localStorage.setItem('access_token', token);
}

function setRefreshToken(token) {
    localStorage.setItem('refresh_token', token);
}

function removeTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
}

// User Management
let currentUser = null;

async function loadCurrentUser() {
    try {
        const resp = await apiFetch('/api/auth/me');
        if (resp.ok) {
            currentUser = await resp.json();
            return currentUser;
        }
    } catch (e) {
        console.error('Failed to load user', e);
    }
    return null;
}

// API Fetch Wrapper with Authentication
async function apiFetch(url, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const resp = await fetch(url, { ...options, headers });
    
    // Auto-redirect on 401 Unauthorized
    if (resp.status === 401) {
        removeTokens();
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
    }
    
    return resp;
}

// Form Data API Fetch (for file uploads)
async function apiFetchFormData(url, formData) {
    const token = getToken();
    const headers = {};
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const resp = await fetch(url, {
        method: 'POST',
        headers: headers,
        body: formData
    });
    
    if (resp.status === 401) {
        removeTokens();
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
    }
    
    return resp;
}

// Toast Notifications
function showToast(message, type = 'success') {
    const colors = {
        success: 'bg-emerald-500',
        error: 'bg-red-500',
        warning: 'bg-amber-500',
        info: 'bg-blue-500'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${colors[type] || colors.success} text-white`;
    toast.style.cssText = `
        position: fixed;
        top: 1rem;
        right: 1rem;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        font-weight: 500;
        z-index: 9999;
        animation: slideIn 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Utility Functions
function formatDate(isoDate) {
    if (!isoDate) return '-';
    
    const date = new Date(isoDate);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatDateSimple(isoDate) {
    if (!isoDate) return '-';
    
    const date = new Date(isoDate);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatTime(isoDate) {
    if (!isoDate) return '-';
    
    const date = new Date(isoDate);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + sizes[i];
}

function formatNumber(num) {
    if (num === null || num === undefined) return '-';
    return num.toLocaleString();
}

function statusBadge(status) {
    const statusClasses = {
        'pending': 'status-pending',
        'processing': 'status-processing',
        'completed': 'status-completed',
        'approved': 'status-approved',
        'rejected': 'status-rejected',
        'review': 'status-review',
        'unknown': 'status-unknown',
        'duplicate': 'status-duplicate',
        'failed': 'status-failed'
    };
    
    const cls = statusClasses[status] || 'status-unknown';
    const displayName = status ? status.toUpperCase() : 'UNKNOWN';
    
    return `<span class="status-badge ${cls}">${displayName}</span>`;
}

// Confidence Bar
function confidenceBar(confidence) {
    const percentage = confidence ? Math.round(confidence * 100) : 0;
    const colorClass = percentage >= 85 ? 'confidence-high' : 
                        percentage >= 70 ? 'confidence-medium' : 'confidence-low';
    
    return `
        <div class="progress-bar w-24">
            <div class="progress-fill ${colorClass}" style="width: ${percentage}%"></div>
        </div>
        <span class="text-xs text-slate-500">${percentage}%</span>
    `;
}

// Modal Management
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
}

// Initialize all modals to close when clicking outside
function initializeModals() {
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeModal(modal.id);
            }
        });
    });
}

// Logout Function
function logout() {
    apiFetch('/api/auth/logout', { method: 'POST' })
        .finally(() => {
            removeTokens();
            window.location.href = '/login';
        });
}

// Validate Email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Debounce Function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Local Storage Helpers
function saveToLocalStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
        console.error('Failed to save to localStorage', e);
    }
}

function getFromLocalStorage(key) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : null;
    } catch (e) {
        console.error('Failed to read from localStorage', e);
        return null;
    }
}

function removeFromLocalStorage(key) {
    try {
        localStorage.removeItem(key);
    } catch (e) {
        console.error('Failed to remove from localStorage', e);
    }
}

// Clipboard Copy
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success');
    } catch (e) {
        console.error('Failed to copy to clipboard', e);
        showToast('Failed to copy', 'error');
    }
}

// Initialize Common Functions
document.addEventListener('DOMContentLoaded', () => {
    initializeModals();
});

// Export functions for use in templates
window.DMS = {
    API_BASE,
    getToken,
    setToken,
    setRefreshToken,
    removeTokens,
    loadCurrentUser,
    apiFetch,
    apiFetchFormData,
    showToast,
    formatDate,
    formatDateSimple,
    formatTime,
    formatFileSize,
    formatNumber,
    statusBadge,
    confidenceBar,
    openModal,
    closeModal,
    logout,
    isValidEmail,
    debounce,
    saveToLocalStorage,
    getFromLocalStorage,
    removeFromLocalStorage,
    copyToClipboard,
    currentUser
};