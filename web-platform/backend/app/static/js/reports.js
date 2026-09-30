/**
 * Reports JavaScript
 * Handles report generation and management.
 */

document.addEventListener('DOMContentLoaded', () => {
    loadCurrentUser();
    loadReportStats();
    loadUsersForFilter();
    setupDateDefaults();
    setupReportTypeListener();
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

function setupDateDefaults() {
    const endDateInput = document.getElementById('endDate');
    const startDateInput = document.getElementById('startDate');
    
    // Set end date to today
    const today = new Date();
    endDateInput.value = today.toISOString().split('T')[0];
    
    // Set start date to 30 days ago
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(today.getDate() - 30);
    startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
}

function setupReportTypeListener() {
    const reportTypeSelect = document.getElementById('reportType');
    const customFilters = document.getElementById('customFilters');
    
    reportTypeSelect.addEventListener('change', () => {
        if (reportTypeSelect.value === 'custom') {
            customFilters.classList.remove('hidden');
        } else {
            customFilters.classList.add('hidden');
        }
    });
}

async function loadUsersForFilter() {
    try {
        const resp = await apiFetch('/api/admin/users');
        if (resp.ok) {
            const data = await resp.json();
            const select = document.getElementById('userFilter');
            
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

async function generateReport() {
    const reportType = document.getElementById('reportType').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const reportFormat = document.getElementById('reportFormat').value;
    const userId = document.getElementById('userFilter').value || null;
    const documentType = document.getElementById('documentType').value || null;
    const actionFilter = document.getElementById('actionFilter').value || null;
    
    if (!startDate || !endDate) {
        showToast('Please select date range', 'warning');
        return;
    }
    
    if (new Date(startDate) > new Date(endDate)) {
        showToast('Start date must be before end date', 'warning');
        return;
    }
    
    try {
        // Show status section
        const statusSection = document.getElementById('reportStatus');
        const statusContent = document.getElementById('statusContent');
        statusSection.classList.remove('hidden');
        statusContent.innerHTML = `
            <div class="flex items-center gap-3">
                <i class="fas fa-circle-notch fa-spin text-blue-500"></i>
                <span class="text-slate-600">Generating report...</span>
            </div>
        `;
        
        // For small datasets, use synchronous endpoint
        if (reportType === 'access_log') {
            const url = `/api/admin/reports/access?start_date=${startDate}&end_date=${endDate}${userId ? '&user_id=' + userId : ''}`;
            window.open(url, '_blank');
            hideReportStatus();
        } else if (reportType === 'document_activity') {
            const url = `/api/admin/reports/activity?start_date=${startDate}&end_date=${endDate}`;
            window.open(url, '_blank');
            hideReportStatus();
        } else if (reportType === 'user_activity') {
            const url = `/api/admin/reports/user?start_date=${startDate}&end_date=${endDate}${userId ? '&user_id=' + userId : ''}`;
            window.open(url, '_blank');
            hideReportStatus();
        } else {
            // For custom or large reports, use async endpoint
            const resp = await apiFetch('/api/admin/reports/generate', {
                method: 'POST',
                body: JSON.stringify({
                    report_type: reportType,
                    start_date: startDate + 'T00:00:00',
                    end_date: endDate + 'T23:59:59',
                    user_id: userId ? parseInt(userId) : null,
                    document_type: documentType,
                    action_filter: actionFilter,
                    format: reportFormat
                })
            });
            
            if (resp.ok) {
                const data = await resp.json();
                statusContent.innerHTML = `
                    <div class="flex items-center gap-3">
                        <i class="fas fa-check-circle text-green-500"></i>
                        <span class="text-slate-600">Report generation started. Report ID: ${data.report_id}</span>
                    </div>
                    <div class="mt-3">
                        <button onclick="checkReportStatus('${data.report_id}')" class="btn-secondary text-sm">
                            Check Status
                        </button>
                    </div>
                `;
                
                // Poll for completion
                pollReportStatus(data.report_id);
            } else {
                const error = await resp.json();
                statusContent.innerHTML = `
                    <div class="flex items-center gap-3">
                        <i class="fas fa-exclamation-circle text-red-500"></i>
                        <span class="text-red-600">Failed to generate report: ${error.detail}</span>
                    </div>
                `;
            }
        }
        
        loadReportStats();
    } catch (e) {
        console.error('Report generation error:', e);
        showToast('Failed to generate report', 'error');
    }
}

async function checkReportStatus(reportId) {
    try {
        const resp = await apiFetch(`/api/admin/reports/status/${reportId}`);
        if (resp.ok) {
            const data = await resp.json();
            
            const statusContent = document.getElementById('statusContent');
            if (data.status === 'completed') {
                statusContent.innerHTML = `
                    <div class="flex items-center gap-3">
                        <i class="fas fa-check-circle text-green-500"></i>
                        <span class="text-slate-600">Report completed successfully!</span>
                    </div>
                    <div class="mt-3">
                        <a href="${data.download_url}" download class="btn-primary text-sm">
                            <i class="fas fa-download mr-2"></i>Download Report
                        </a>
                    </div>
                `;
            } else if (data.status === 'failed') {
                statusContent.innerHTML = `
                    <div class="flex items-center gap-3">
                        <i class="fas fa-exclamation-circle text-red-500"></i>
                        <span class="text-red-600">Report generation failed</span>
                    </div>
                `;
            } else {
                statusContent.innerHTML = `
                    <div class="flex items-center gap-3">
                        <i class="fas fa-circle-notch fa-spin text-blue-500"></i>
                        <span class="text-slate-600">Report is still processing...</span>
                    </div>
                `;
            }
        }
    } catch (e) {
        console.error('Status check error:', e);
    }
}

function pollReportStatus(reportId) {
    const maxAttempts = 30; // 5 minutes max (10 seconds per check)
    let attempts = 0;
    
    const interval = setInterval(() => {
        attempts++;
        if (attempts >= maxAttempts) {
            clearInterval(interval);
            return;
        }
        
        checkReportStatus(reportId);
    }, 10000);
}

function hideReportStatus() {
    document.getElementById('reportStatus').classList.add('hidden');
}

async function loadReportStats() {
    try {
        const resp = await apiFetch('/api/admin/reports/stats');
        if (resp.ok) {
            const stats = await resp.json();
            document.getElementById('totalReports').textContent = stats.total_reports;
            document.getElementById('successfulReports').textContent = stats.successful_reports;
            document.getElementById('failedReports').textContent = stats.failed_reports;
            document.getElementById('lastGenerated').textContent = stats.last_generated ? formatDate(stats.last_generated) : 'Never';
        }
    } catch (e) {
        console.error('Failed to load report stats:', e);
    }
}

function scheduleReport() {
    document.getElementById('scheduleModal').classList.remove('hidden');
}

function closeScheduleModal() {
    document.getElementById('scheduleModal').classList.add('hidden');
}

async function confirmSchedule(event) {
    event.preventDefault();
    
    const reportType = document.getElementById('scheduleReportType').value;
    const frequency = document.getElementById('scheduleFrequency').value;
    const email = document.getElementById('scheduleEmail').value;
    
    try {
        const resp = await apiFetch('/api/admin/reports/schedule', {
            method: 'POST',
            body: JSON.stringify({
                report_type: reportType,
                frequency: frequency,
                recipient_email: email,
                enabled: true
            })
        });
        
        if (resp.ok) {
            showToast('Report scheduled successfully', 'success');
            closeScheduleModal();
        } else {
            showToast('Failed to schedule report', 'error');
        }
    } catch (e) {
        console.error('Schedule error:', e);
        showToast('Failed to schedule report', 'error');
    }
}

async function cleanupOldReports() {
    if (!confirm('Delete reports older than 30 days?')) {
        return;
    }
    
    try {
        const resp = await apiFetch('/api/admin/reports/cleanup?retention_days=30', {
            method: 'POST'
        });
        
        if (resp.ok) {
            const data = await resp.json();
            showToast(`Cleaned up ${data.deleted_count} old reports`, 'success');
            loadReportStats();
        } else {
            showToast('Failed to cleanup reports', 'error');
        }
    } catch (e) {
        console.error('Cleanup error:', e);
        showToast('Failed to cleanup reports', 'error');
    }
}