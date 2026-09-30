/**
 * 2FA JavaScript
 * Handles Two-Factor Authentication setup and management in settings.
 */

document.addEventListener('DOMContentLoaded', () => {
    loadCurrentUser();
    load2FAStatus();
});

async function loadCurrentUser() {
    try {
        const resp = await apiFetch('/api/auth/me');
        if (resp.ok) {
            const user = await resp.json();
            currentUser = user;
        }
    } catch (e) {
        console.error('Failed to load user', e);
    }
}

async function load2FAStatus() {
    try {
        const resp = await apiFetch('/api/2fa/status');
        if (resp.ok) {
            const status = await resp.json();
            update2FAUI(status);
        }
    } catch (e) {
        console.error('Failed to load 2FA status:', e);
    }
}

function update2FAUI(status) {
    const setupSection = document.getElementById('2faSetupSection');
    const manageSection = document.getElementById('2faManageSection');
    const enabledBadge = document.getElementById('2faEnabledBadge');
    
    if (status.totp_enabled) {
        setupSection?.classList.add('hidden');
        manageSection?.classList.remove('hidden');
        if (enabledBadge) {
            enabledBadge.textContent = '2FA Enabled';
            enabledBadge.className = 'status-badge status-approved';
        }
    } else {
        setupSection?.classList.remove('hidden');
        manageSection?.classList.add('hidden');
        if (enabledBadge) {
            enabledBadge.textContent = '2FA Disabled';
            enabledBadge.className = 'status-badge status-unknown';
        }
    }
    
    if (status.has_backup_codes) {
        document.getElementById('hasBackupCodes').textContent = 'Yes';
    } else {
        document.getElementById('hasBackupCodes').textContent = 'No';
    }
}

async function setup2FA() {
    try {
        const resp = await apiFetch('/api/2fa/setup', {
            method: 'POST'
        });
        
        if (resp.ok) {
            const data = await resp.json();
            showQRCode(data);
            showBackupCodes(data.backup_codes);
        } else {
            const error = await resp.json();
            showToast(error.detail || 'Failed to setup 2FA', 'error');
        }
    } catch (e) {
        console.error('2FA setup error:', e);
        showToast('Failed to setup 2FA', 'error');
    }
}

function showQRCode(data) {
    const qrSection = document.getElementById('qrCodeSection');
    const qrImage = document.getElementById('qrCodeImage');
    const secretText = document.getElementById('totpSecret');
    
    qrSection.classList.remove('hidden');
    qrImage.src = data.qr_code_url;
    secretText.textContent = data.secret;
}

function showBackupCodes(codes) {
    const backupSection = document.getElementById('backupCodesSection');
    const codesContainer = document.getElementById('backupCodesContainer');
    
    backupSection.classList.remove('hidden');
    codesContainer.innerHTML = codes.map(code => 
        `<div class="p-2 bg-slate-100 rounded text-center font-mono text-sm">${code}</div>`
    ).join('');
}

async function verifySetupOTP() {
    const otpInput = document.getElementById('setupOTPInput');
    const otp = otpInput.value.trim();
    
    if (otp.length !== 6) {
        showToast('Please enter a 6-digit OTP code', 'warning');
        return;
    }
    
    try {
        const resp = await apiFetch('/api/2fa/verify-setup', {
            method: 'POST',
            body: JSON.stringify({ otp: otp })
        });
        
        if (resp.ok) {
            const data = await resp.json();
            showToast(data.message, 'success');
            
            // Show enable button
            document.getElementById('verifyButton').classList.add('hidden');
            document.getElementById('enableButton').classList.remove('hidden');
        } else {
            const error = await resp.json();
            showToast(error.detail || 'Invalid OTP', 'error');
            otpInput.value = '';
        }
    } catch (e) {
        console.error('OTP verification error:', e);
        showToast('Failed to verify OTP', 'error');
    }
}

async function enable2FA() {
    try {
        const resp = await apiFetch('/api/2fa/enable', {
            method: 'POST'
        });
        
        if (resp.ok) {
            const data = await resp.json();
            showToast(data.message, 'success');
            load2FAStatus();
            hideSetupSection();
        } else {
            const error = await resp.json();
            showToast(error.detail || 'Failed to enable 2FA', 'error');
        }
    } catch (e) {
        console.error('2FA enable error:', e);
        showToast('Failed to enable 2FA', 'error');
    }
}

async function disable2FA() {
    const otpInput = document.getElementById('disableOTPInput');
    const otp = otpInput.value.trim();
    
    if (otp.length !== 6) {
        showToast('Please enter your current OTP code', 'warning');
        return;
    }
    
    try {
        const resp = await apiFetch('/api/2fa/disable', {
            method: 'POST',
            body: JSON.stringify({ otp: otp })
        });
        
        if (resp.ok) {
            showToast('2FA disabled successfully', 'success');
            otpInput.value = '';
            load2FAStatus();
        } else {
            const error = await resp.json();
            showToast(error.detail || 'Failed to disable 2FA', 'error');
        }
    } catch (e) {
        console.error('2FA disable error:', e);
        showToast('Failed to disable 2FA', 'error');
    }
}

async function regenerateBackupCodes() {
    if (!confirm('This will invalidate your existing backup codes. Continue?')) {
        return;
    }
    
    try {
        const resp = await apiFetch('/api/2fa/regenerate-backup-codes', {
            method: 'POST'
        });
        
        if (resp.ok) {
            const data = await resp.json();
            showBackupCodes(data.backup_codes);
            showToast('Backup codes regenerated successfully', 'success');
        } else {
            const error = await resp.json();
            showToast(error.detail || 'Failed to regenerate backup codes', 'error');
        }
    } catch (e) {
        console.error('Backup codes regeneration error:', e);
        showToast('Failed to regenerate backup codes', 'error');
    }
}

function hideSetupSection() {
    document.getElementById('qrCodeSection').classList.add('hidden');
    document.getElementById('backupCodesSection').classList.add('hidden');
    document.getElementById('setupOTPInput').value = '';
    document.getElementById('verifyButton').classList.remove('hidden');
    document.getElementById('enableButton').classList.add('hidden');
}