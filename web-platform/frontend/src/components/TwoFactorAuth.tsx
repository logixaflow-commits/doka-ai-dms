import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Shield, Key, Copy, CheckCircle, AlertCircle, RefreshCw, Smartphone } from 'lucide-react';

const API_BASE = '/api';

interface TwoFactorSetup {
  qr_code_url: string;
  secret: string;
  backup_codes: string[];
}

interface TwoFactorStatus {
  enabled: boolean;
  verified: boolean;
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

export default function TwoFactorAuth() {
  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [setupData, setSetupData] = useState<TwoFactorSetup | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Verification state
  const [otp, setOtp] = useState('');
  const [verifying, setVerifying] = useState(false);
  
  // Disable state
  const [disabling, setDisabling] = useState(false);
  const [confirmDisable, setConfirmDisable] = useState(false);

  useEffect(() => {
    loadStatus();
  }, []);

  async function loadStatus() {
    try {
      setLoading(true);
      const response = await apiFetch(`${API_BASE}/2fa/status`);
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
    } catch (err) {
      setError('Failed to load 2FA status');
      console.error('Failed to load 2FA status:', err);
    } finally {
      setLoading(false);
    }
  }

  async function setupTwoFactor() {
    try {
      setLoading(true);
      setError(null);
      const response = await apiFetch(`${API_BASE}/2fa/setup`, {
        method: 'POST',
      });
      if (response.ok) {
        const data = await response.json();
        setSetupData(data);
      } else {
        setError('Failed to setup 2FA');
      }
    } catch (err) {
      setError('Error setting up 2FA');
      console.error('Failed to setup 2FA:', err);
    } finally {
      setLoading(false);
    }
  }

  async function verifyOTP() {
    if (!otp || otp.length !== 6) {
      setError('Please enter a 6-digit OTP');
      return;
    }

    try {
      setVerifying(true);
      setError(null);
      const response = await apiFetch(`${API_BASE}/2fa/verify`, {
        method: 'POST',
        body: JSON.stringify({ otp }),
      });
      if (response.ok) {
        setSuccess('2FA enabled successfully!');
        setSetupData(null);
        setOtp('');
        loadStatus();
      } else {
        const data = await response.json();
        setError(data.detail || 'Invalid OTP');
      }
    } catch (err) {
      setError('Verification failed');
      console.error('Failed to verify OTP:', err);
    } finally {
      setVerifying(false);
    }
  }

  async function disableTwoFactor() {
    try {
      setDisabling(true);
      setError(null);
      const response = await apiFetch(`${API_BASE}/2fa/disable`, {
        method: 'POST',
      });
      if (response.ok) {
        setSuccess('2FA disabled successfully!');
        setConfirmDisable(false);
        loadStatus();
      } else {
        setError('Failed to disable 2FA');
      }
    } catch (err) {
      setError('Error disabling 2FA');
      console.error('Failed to disable 2FA:', err);
    } finally {
      setDisabling(false);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    setSuccess('Copied to clipboard!');
    setTimeout(() => setSuccess(null), 2000);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500">Loading 2FA settings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Two-Factor Authentication</h2>
        <p className="text-slate-500 dark:text-slate-400">
          Add an extra layer of security to your account
        </p>
      </div>

      {/* Status Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            2FA Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          {status?.enabled ? (
            <div className="flex items-center gap-3">
              <CheckCircle className="w-6 h-6 text-green-500" />
              <div>
                <div className="font-medium text-green-600 dark:text-green-400">
                  Two-Factor Authentication is Enabled
                </div>
                <div className="text-sm text-slate-500">
                  Your account is protected with 2FA
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-amber-500" />
              <div>
                <div className="font-medium text-amber-600 dark:text-amber-400">
                  Two-Factor Authentication is Disabled
                </div>
                <div className="text-sm text-slate-500">
                  Enable 2FA to add extra security to your account
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Setup Process */}
      {!status?.enabled && (
        <Card>
          <CardHeader>
            <CardTitle>Setup Two-Factor Authentication</CardTitle>
            <CardDescription>
              Use an authenticator app like Google Authenticator, Authy, or Microsoft Authenticator
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!setupData ? (
              <Button onClick={setupTwoFactor} disabled={loading}>
                <Smartphone className="w-4 h-4 mr-2" />
                Setup 2FA
              </Button>
            ) : (
              <div className="space-y-6">
                {/* QR Code */}
                <div className="flex flex-col items-center">
                  <div className="bg-white p-4 rounded-lg border">
                    {setupData.qr_code_url && (
                      <img 
                        src={setupData.qr_code_url} 
                        alt="QR Code" 
                        className="w-48 h-48"
                      />
                    )}
                  </div>
                  <p className="text-sm text-slate-500 mt-2">
                    Scan this QR code with your authenticator app
                  </p>
                </div>

                {/* Secret Key */}
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Or enter this code manually:
                  </label>
                  <div className="flex gap-2">
                    <Input 
                      value={setupData.secret} 
                      readOnly 
                      className="font-mono"
                    />
                    <Button 
                      onClick={() => copyToClipboard(setupData.secret)}
                      variant="outline"
                      size="icon"
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                {/* Verification */}
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Enter the 6-digit code from your authenticator app:
                  </label>
                  <div className="flex gap-2">
                    <Input
                      type="text"
                      placeholder="123456"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                      maxLength={6}
                      className="font-mono text-center text-lg tracking-widest"
                    />
                    <Button 
                      onClick={verifyOTP}
                      disabled={verifying || otp.length !== 6}
                    >
                      {verifying ? 'Verifying...' : 'Verify'}
                    </Button>
                  </div>
                </div>

                {/* Backup Codes */}
                <div className="bg-amber-50 dark:bg-amber-950 p-4 rounded-lg">
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <Key className="w-4 h-4" />
                    Backup Codes
                  </h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                    Save these backup codes in a safe place. You can use them to access your account if you lose your authenticator device.
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {setupData.backup_codes.map((code, index) => (
                      <code key={index} className="bg-white dark:bg-slate-900 p-2 rounded text-sm font-mono">
                        {code}
                      </code>
                    ))}
                  </div>
                </div>

                <Button 
                  onClick={() => setSetupData(null)}
                  variant="outline"
                >
                  Cancel
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Disable 2FA */}
      {status?.enabled && (
        <Card>
          <CardHeader>
            <CardTitle>Disable Two-Factor Authentication</CardTitle>
            <CardDescription>
              Remove 2FA protection from your account (not recommended)
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!confirmDisable ? (
              <Button 
                onClick={() => setConfirmDisable(true)}
                variant="destructive"
              >
                Disable 2FA
              </Button>
            ) : (
              <div className="space-y-4">
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Are you sure you want to disable 2FA? This will make your account less secure.
                  </AlertDescription>
                </Alert>
                <div className="flex gap-2">
                  <Button 
                    onClick={disableTwoFactor}
                    disabled={disabling}
                    variant="destructive"
                  >
                    {disabling ? 'Disabling...' : 'Yes, Disable 2FA'}
                  </Button>
                  <Button 
                    onClick={() => setConfirmDisable(false)}
                    variant="outline"
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Alerts */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
