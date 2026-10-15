/**
 * Enterprise DMS - Dashboard JavaScript
 * Handles main dashboard functionality including social media inbox
 */

// Global variables
let selectedDocuments = new Set();
let socialDailyData = {};
let currentSocialDateFilter = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentUser();
    loadDashboard();
    loadSocialMediaStats();
    initRealtimeUpdates();
    initializeModals();
});

// Load dashboard stats
async function loadDashboard() {
    try {
        // Load main dashboard stats
        const statsResp = await apiFetch('/api/admin/stats');
        if (statsResp.ok) {
            const stats = await statsResp.json();
            updateDashboardStats(stats);
        }

        // Load pending documents
        await loadPendingDocuments();

        // Load analytics and charts
        await loadAnalytics();
        await loadExpiringSoon();
    } catch (e) {
        console.error('Failed to load dashboard:', e);
    }
}

// Update dashboard stats
function updateDashboardStats(stats) {
    document.getElementById('statPending').textContent = stats.pending || 0;
    document.getElementById('statApprovedToday').textContent = stats.approved_today || 0;
    document.getElementById('statTotal').textContent = stats.total_documents || 0;
    document.getElementById('statFailed').textContent = stats.failed || 0;

    // Update sidebar counts
    if (stats.pending > 0) {
        const badge = document.getElementById('sidebarPendingCount');
        badge.textContent = stats.pending;
        badge.classList.remove('hidden');
    }
}

// Load pending documents
async function loadPendingDocuments() {
    try {
        const resp = await apiFetch('/api/documents/pending?page=1&page_size=10');
        if (resp.ok) {
            const data = await resp.json();
            renderPendingTable(data.items);
        }
    } catch (e) {
        console.error('Failed to load pending documents:', e);
    }
}

// Render pending documents table
function renderPendingTable(documents) {
    const tbody = document.getElementById('pendingTable');
    
    if (!documents || documents.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="py-8 text-center text-slate-500">
                    No pending documents
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = documents.map(doc => `
        <tr class="border-b border-slate-100 table-row-hover">
            <td class="py-3 px-4">
                <input type="checkbox" onchange="toggleSelection(${doc.id})" ${selectedDocuments.has(doc.id) ? 'checked' : ''}>
            </td>
            <td class="py-3 px-4">
                <div class="font-medium text-slate-800">${doc.original_filename}</div>
                <div class="text-xs text-slate-500">${formatFileSize(doc.file_size)}</div>
            </td>
            <td class="py-3 px-4">
                ${doc.category ? statusBadge(doc.category) : '<span class="text-slate-400">-</span>'}
            </td>
            <td class="py-3 px-4">
                ${doc.confidence ? confidenceBar(doc.confidence) : '-'}
            </td>
            <td class="py-3 px-4">
                ${statusBadge(doc.status)}
            </td>
            <td class="py-3 px-4 text-sm text-slate-600">
                ${formatDate(doc.created_at)}
            </td>
            <td class="py-3 px-4">
                <div class="flex items-center gap-2">
                    <a href="/documents/${doc.id}" class="text-blue-600 hover:text-blue-800 text-sm">View</a>
                </div>
            </td>
        </tr>
    `).join('');
}

// Toggle document selection
function toggleSelection(docId) {
    if (selectedDocuments.has(docId)) {
        selectedDocuments.delete(docId);
    } else {
        selectedDocuments.add(docId);
    }
    updateSelectAllState();
}

// Toggle select all
function toggleSelectAll() {
    const selectAll = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('#pendingTable input[type="checkbox"]');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll.checked;
        const docId = parseInt(checkbox.parentElement.parentElement.querySelector('a').getAttribute('href').split('/')[2]);
        if (selectAll.checked) {
            selectedDocuments.add(docId);
        } else {
            selectedDocuments.delete(docId);
        }
    });
}

// Update select all state
function updateSelectAllState() {
    const selectAll = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('#pendingTable input[type="checkbox"]');
    
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    selectAll.checked = allChecked;
}

// Bulk approve
async function bulkApprove() {
    if (selectedDocuments.size === 0) {
        showToast('Please select documents to approve', 'warning');
        return;
    }

    const resp = await apiFetch('/api/documents/bulk/approve', {
        method: 'POST',
        body: JSON.stringify({
            document_ids: Array.from(selectedDocuments),
            target_folder: 'Approved'
        })
    });

    if (resp.ok) {
        const result = await resp.json();
        showToast(`Approved ${result.success_count} documents successfully`);
        selectedDocuments.clear();
        loadPendingDocuments();
        loadDashboard();
    }
}

// Bulk reject
async function bulkReject() {
    if (selectedDocuments.size === 0) {
        showToast('Please select documents to reject', 'warning');
        return;
    }

    const reason = prompt('Rejection reason (optional):');
    
    const resp = await apiFetch('/api/documents/bulk/reject', {
        method: 'POST',
        body: JSON.stringify({
            document_ids: Array.from(selectedDocuments),
            reason: reason
        })
    });

    if (resp.ok) {
        const result = await resp.json();
        showToast(`Rejected ${result.success_count} documents successfully`);
        selectedDocuments.clear();
        loadPendingDocuments();
        loadDashboard();
    }
}

// ============================================================================
// SOCIAL MEDIA INBOX FUNCTIONS
// ============================================================================

// Load social media stats
async function loadSocialMediaStats() {
    try {
        // For now, we'll use a simplified approach
        // In production, this would call a dedicated endpoint
        const resp = await apiFetch('/api/documents?status=pending_review&page=1&page_size=100');
        if (resp.ok) {
            const data = await resp.json();
            const socialDocs = data.items.filter(doc => doc.source);
            updateSocialStats(socialDocs);
        }
    } catch (e) {
        console.error('Failed to load social media stats:', e);
    }
}

// Update social media stats
function updateSocialStats(socialDocs) {
    const socialPending = socialDocs.filter(doc => doc.status === 'pending_review').length;
    const viberCount = socialDocs.filter(doc => doc.source === 'Viber').length;
    const whatsappCount = socialDocs.filter(doc => doc.source === 'WhatsApp').length;
    
    // Get today's count
    const today = new Date().toISOString().split('T')[0];
    const todayCount = socialDocs.filter(doc => doc.created_at && doc.created_at.startsWith(today)).length;

    document.getElementById('statSocialPending').textContent = socialPending;
    document.getElementById('statViber').textContent = viberCount;
    document.getElementById('statWhatsApp').textContent = whatsappCount;
    document.getElementById('statSocialToday').textContent = todayCount;

    // Update sidebar social count
    if (socialPending > 0) {
        const badge = document.getElementById('sidebarSocialCount');
        badge.textContent = socialPending;
        badge.classList.remove('hidden');
    }

    // Group by date for daily view
    socialDailyData = groupSocialByDate(socialDocs);
}

// Group social documents by date
function groupSocialByDate(documents) {
    const grouped = {};
    
    documents.forEach(doc => {
        const date = doc.created_at ? doc.created_at.split('T')[0] : 'Unknown';
        if (!grouped[date]) {
            grouped[date] = [];
        }
        grouped[date].push(doc);
    });

    return grouped;
}

// Show social inbox section
function showSocialInbox() {
    const section = document.getElementById('socialInboxSection');
    section.classList.remove('hidden');
    renderSocialDailyView();
}

// Hide social inbox section
function hideSocialInbox() {
    const section = document.getElementById('socialInboxSection');
    section.classList.add('hidden');
}

// Render social daily view
function renderSocialDailyView() {
    const container = document.getElementById('socialDailyView');
    const sourceFilter = document.getElementById('socialSourceFilter').value;

    if (!socialDailyData || Object.keys(socialDailyData).length === 0) {
        container.innerHTML = `
            <p class="text-slate-500 text-center py-8">
                No social media documents pending review
            </p>
        `;
        return;
    }

    let html = '';
    const sortedDates = Object.keys(socialDailyData).sort().reverse();

    sortedDates.forEach(date => {
        let docs = socialDailyData[date];
        
        // Apply source filter
        if (sourceFilter) {
            docs = docs.filter(doc => doc.source === sourceFilter);
        }

        if (docs.length === 0) return;

        html += `
            <div class="bg-slate-50 rounded-lg p-4">
                <div class="flex items-center justify-between mb-3">
                    <h4 class="font-bold text-slate-800">${formatDate(date)}</h4>
                    <div class="flex items-center gap-2">
                        <span class="text-sm text-slate-600">${docs.length} documents</span>
                        <button onclick="bulkApproveDate('${date}')" class="btn-primary text-sm">
                            <i class="fas fa-check mr-1"></i>Approve All
                        </button>
                        <button onclick="bulkRejectDate('${date}')" class="btn-secondary text-sm">
                            <i class="fas fa-times mr-1"></i>Reject All
                        </button>
                    </div>
                </div>
                <div class="space-y-2">
                    ${docs.map(doc => `
                        <div class="flex items-center justify-between bg-white rounded p-3 border border-slate-200">
                            <div class="flex items-center gap-3">
                                <span class="status-badge status-unknown">${doc.source || 'Unknown'}</span>
                                <span class="font-medium text-slate-800">${doc.original_filename}</span>
                                <span class="text-xs text-slate-500">${doc.category || 'Unknown'}</span>
                            </div>
                            <a href="/documents/${doc.id}" class="text-blue-600 hover:text-blue-800 text-sm">View</a>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Load social documents by source filter
function loadSocialBySource() {
    renderSocialDailyView();
}

// Bulk approve all documents for a specific date
async function bulkApproveDate(date) {
    const docs = socialDailyData[date] || [];
    const sourceFilter = document.getElementById('socialSourceFilter').value;
    
    let targetDocs = docs;
    if (sourceFilter) {
        targetDocs = docs.filter(doc => doc.source === sourceFilter);
    }

    const docIds = targetDocs.map(doc => doc.id);
    
    if (docIds.length === 0) {
        showToast('No documents to approve', 'warning');
        return;
    }

    if (!confirm(`Approve ${docIds.length} documents from ${date}?`)) {
        return;
    }

    const resp = await apiFetch('/api/documents/bulk/approve', {
        method: 'POST',
        body: JSON.stringify({
            document_ids: docIds,
            target_folder: 'Social_Media_Approved'
        })
    });

    if (resp.ok) {
        const result = await resp.json();
        showToast(`Approved ${result.success_count} documents successfully`);
        loadSocialMediaStats();
        renderSocialDailyView();
    }
}

// Bulk reject all documents for a specific date
async function bulkRejectDate(date) {
    const docs = socialDailyData[date] || [];
    const sourceFilter = document.getElementById('socialSourceFilter').value;
    
    let targetDocs = docs;
    if (sourceFilter) {
        targetDocs = docs.filter(doc => doc.source === sourceFilter);
    }

    const docIds = targetDocs.map(doc => doc.id);
    
    if (docIds.length === 0) {
        showToast('No documents to reject', 'warning');
        return;
    }

    const reason = prompt('Rejection reason (optional):');
    
    const resp = await apiFetch('/api/documents/bulk/reject', {
        method: 'POST',
        body: JSON.stringify({
            document_ids: docIds,
            reason: reason
        })
    });

    if (resp.ok) {
        const result = await resp.json();
        showToast(`Rejected ${result.success_count} documents successfully`);
        loadSocialMediaStats();
        renderSocialDailyView();
    }
}

// ============================================================================
// REAL-TIME UPDATES
// ============================================================================

// Initialize real-time updates
// ============================================================================
// SSE CONNECTION WITH EXPONENTIAL BACKOFF RECONNECTION
// ============================================================================

let eventSource = null;
let sseRetryCount = 0;
let sseRetryDelays = [1, 5, 15, 30, 60]; // Exponential backoff: 1s, 5s, 15s, 30s, 60s
let sseMaxRetries = sseRetryDelays.length;
let sseReconnectTimer = null;

function initRealtimeUpdates() {
    connectSSE();
    updateConnectionStatus('connecting');
}

function connectSSE() {
    try {
        // Close existing connection if any
        if (eventSource) {
            eventSource.close();
        }
        
        eventSource = new EventSource('/api/realtime/events');
        
        eventSource.onopen = function() {
            console.log('SSE connection established');
            sseRetryCount = 0; // Reset retry count on successful connection
            updateConnectionStatus('connected');
            
            // Re-sync dashboard data when reconnected
            loadDashboard();
            loadSocialMediaStats();
        };
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'pending_count_update') {
                document.getElementById('statPending').textContent = data.data.count;
                loadPendingDocuments();
            } else if (data.type === 'stats_update') {
                updateDashboardStats(data.data);
            } else if (data.type === 'social_stats_update') {
                updateSocialStats(data.data);
            }
        };
        
        eventSource.onerror = function(error) {
            console.error('SSE error:', error);
            eventSource.close();
            updateConnectionStatus('disconnected');
            scheduleSSEReconnect();
        };
        
    } catch (e) {
        console.error('Failed to create SSE connection:', e);
        updateConnectionStatus('failed');
        scheduleSSEReconnect();
    }
}

function scheduleSSEReconnect() {
    // Clear any existing reconnection timer
    if (sseReconnectTimer) {
        clearTimeout(sseReconnectTimer);
    }
    
    // Check if we've exceeded max retries
    if (sseRetryCount >= sseMaxRetries) {
        console.warn('Max SSE reconnection attempts reached, falling back to polling');
        initPolling();
        return;
    }
    
    // Get retry delay for this attempt
    const delay = sseRetryDelays[Math.min(sseRetryCount, sseRetryDelays.length - 1)] * 1000;
    sseRetryCount++;
    
    console.log(`SSE reconnection attempt ${sseRetryCount}/${sseMaxRetries} in ${delay/1000}s`);
    updateConnectionStatus('reconnecting');
    
    // Schedule reconnection
    sseReconnectTimer = setTimeout(() => {
        connectSSE();
    }, delay);
}

function updateConnectionStatus(status) {
    // Update connection status indicator (green/red dot)
    const statusIndicator = document.getElementById('connectionStatus');
    if (statusIndicator) {
        const statusColors = {
            'connected': 'bg-green-500',
            'disconnected': 'bg-red-500',
            'connecting': 'bg-yellow-500',
            'reconnecting': 'bg-orange-500',
            'failed': 'bg-red-600'
        };
        
        const statusTexts = {
            'connected': 'Connected',
            'disconnected': 'Disconnected',
            'connecting': 'Connecting...',
            'reconnecting': 'Reconnecting...',
            'failed': 'Connection Failed'
        };
        
        statusIndicator.className = `w-2 h-2 rounded-full ${statusColors[status] || statusColors['failed']}`;
        statusIndicator.title = statusTexts[status] || status;
    }
}

// Fallback polling
function initPolling() {
    setInterval(() => {
        loadDashboard();
        loadSocialMediaStats();
    }, 30000);
}

// ============================================================================
// ANALYTICS & CHARTS
// ============================================================================

// Load analytics data and render charts
async function loadAnalytics() {
    try {
        const overviewResp = await apiFetch('/api/admin/analytics/overview');
        if (overviewResp.ok) {
            const overview = await overviewResp.json();
            renderCategoryChart(overview.by_category);
            renderStatusChart(overview.by_status);
        }

        const trendsResp = await apiFetch('/api/admin/analytics/trends?days=30');
        if (trendsResp.ok) {
            const trends = await trendsResp.json();
            renderTrendChart(trends.daily_uploads);
        }
    } catch (e) {
        console.error('Failed to load analytics:', e);
    }
}

// Render category bar chart
function renderCategoryChart(categoryData) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    const labels = Object.keys(categoryData);
    const data = Object.values(categoryData);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Documents',
                data: data,
                backgroundColor: 'rgba(59, 130, 246, 0.8)',
                borderColor: 'rgba(59, 130, 246, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

// Render status pie chart
function renderStatusChart(statusData) {
    const ctx = document.getElementById('statusChart').getContext('2d');
    
    const labels = Object.keys(statusData);
    const data = Object.values(statusData);
    
    const colors = {
        'pending': 'rgba(251, 191, 36, 0.8)',
        'processing': 'rgba(59, 130, 246, 0.8)',
        'completed': 'rgba(34, 197, 94, 0.8)',
        'approved': 'rgba(16, 185, 129, 0.8)',
        'rejected': 'rgba(239, 68, 68, 0.8)',
        'failed': 'rgba(220, 38, 38, 0.8)'
    };
    
    const backgroundColor = labels.map(label => colors[label] || 'rgba(156, 163, 175, 0.8)');
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColor
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

// Render upload trend line chart
function renderTrendChart(trendData) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    
    const labels = trendData.map(item => item.date);
    const data = trendData.map(item => item.count);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Documents Uploaded',
                data: data,
                borderColor: 'rgba(59, 130, 246, 1)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

// Load expiring soon documents
async function loadExpiringSoon() {
    try {
        const resp = await apiFetch('/api/documents/expiring-soon');
        if (resp.ok) {
            const data = await resp.json();
            renderExpiringSoon(data.documents);
        }
    } catch (e) {
        console.error('Failed to load expiring soon documents:', e);
    }
}

// Render expiring soon documents
function renderExpiringSoon(documents) {
    const container = document.getElementById('expiringSoon');
    
    if (!documents || documents.length === 0) {
        container.innerHTML = `
            <p class="text-orange-600 text-center py-2">No documents expiring soon</p>
        `;
        return;
    }
    
    container.innerHTML = documents.map(doc => {
        const daysRemaining = Math.ceil((new Date(doc.expiry_date) - new Date()) / (1000 * 60 * 60 * 24));
        const urgencyClass = daysRemaining <= 1 ? 'text-red-600' : daysRemaining <= 3 ? 'text-orange-600' : 'text-yellow-600';
        
        return `
            <div class="flex items-center justify-between p-3 bg-white rounded-lg border border-orange-200">
                <div class="flex-1">
                    <div class="font-medium text-slate-800">${doc.original_filename}</div>
                    <div class="text-sm text-slate-500">Expires: ${formatDate(doc.expiry_date)}</div>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-sm ${urgencyClass} font-medium">${daysRemaining} days</span>
                    <a href="/documents/${doc.id}" class="text-orange-600 hover:text-orange-800 text-sm">View</a>
                </div>
            </div>
        `;
    }).join('');
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

// Confidence bar (re-used from utils.js)
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

// Upload modal
function openUploadModal() {
    openModal('uploadModal');
}