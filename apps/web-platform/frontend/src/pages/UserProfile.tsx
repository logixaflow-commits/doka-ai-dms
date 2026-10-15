import { useState } from 'react';
import { User, Mail, Lock, Bell, Shield, Save } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useFieldValidation, validationRules, ValidationMessage, ValidatedInput, PasswordStrength } from '@/components/FormValidation';
import { success, error } from '@/components/Toast';

export default function UserProfile() {
  const [loading, setLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [apiError, setApiError] = useState('');

  // Profile settings
  const [username, setUsername] = useState(localStorage.getItem('username') || '');
  const [email, setEmail] = useState('user@example.com');

  // Password change
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Notification settings
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(false);

  // Validation
  const usernameValidation = useFieldValidation(username, [validationRules.required(), validationRules.minLength(3)], true);
  const emailValidation = useFieldValidation(email, [validationRules.required(), validationRules.email()], true);
  const newPasswordValidation = useFieldValidation(newPassword, [validationRules.password()], true);
  const confirmPasswordValidation = useFieldValidation(
    confirmPassword,
    [validationRules.match(newPassword, 'Passwords do not match')],
    true
  );

  const handleProfileSave = async () => {
    if (!usernameValidation.validation.isValid || !emailValidation.validation.isValid) {
      usernameValidation.handleBlur();
      emailValidation.handleBlur();
      return;
    }

    setLoading(true);
    setApiError('');

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/users/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ username, email }),
      });

      if (!response.ok) throw new Error('Failed to update profile');

      localStorage.setItem('username', username);
      setSaveSuccess(true);
      success('Profile updated successfully');
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      setApiError('Failed to update profile');
      error('Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async () => {
    if (!currentPassword || !newPasswordValidation.validation.isValid || !confirmPasswordValidation.validation.isValid) {
      newPasswordValidation.handleBlur();
      confirmPasswordValidation.handleBlur();
      return;
    }

    setLoading(true);
    setApiError('');

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (!response.ok) throw new Error('Failed to change password');

      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      success('Password changed successfully');
    } catch {
      setApiError('Failed to change password');
      error('Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  const handleNotificationSave = async () => {
    setLoading(true);
    setApiError('');

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/users/notifications', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          email_notifications: emailNotifications,
          push_notifications: pushNotifications,
        }),
      });

      if (!response.ok) throw new Error('Failed to update notification settings');

      success('Notification settings updated');
    } catch {
      setApiError('Failed to update notification settings');
      error('Failed to update notification settings');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Profile Settings</h1>
        <p className="text-slate-600 dark:text-slate-400 mt-1">Manage your account settings and preferences</p>
      </div>

      {apiError && (
        <Alert variant="destructive">
          <AlertDescription>{apiError}</AlertDescription>
        </Alert>
      )}

      {saveSuccess && (
        <Alert className="bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800">
          <AlertDescription className="text-emerald-800 dark:text-emerald-300">
            Settings saved successfully
          </AlertDescription>
        </Alert>
      )}

      {/* Profile Information */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <User className="w-5 h-5" />
            <CardTitle>Profile Information</CardTitle>
          </div>
          <CardDescription>Update your personal information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <ValidatedInput
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onBlur={usernameValidation.handleBlur}
              validation={usernameValidation.validation}
              touched={usernameValidation.touched}
            />
            <ValidationMessage
              validation={usernameValidation.validation}
              touched={usernameValidation.touched}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
              <ValidatedInput
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={emailValidation.handleBlur}
                validation={emailValidation.validation}
                touched={emailValidation.touched}
                className="pl-10"
              />
            </div>
            <ValidationMessage
              validation={emailValidation.validation}
              touched={emailValidation.touched}
            />
          </div>

          <Button onClick={handleProfileSave} disabled={loading} className="w-full">
            <Save className="w-4 h-4 mr-2" />
            {loading ? 'Saving...' : 'Save Profile'}
          </Button>
        </CardContent>
      </Card>

      {/* Password Change */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Lock className="w-5 h-5" />
            <CardTitle>Change Password</CardTitle>
          </div>
          <CardDescription>Update your password to keep your account secure</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current-password">Current Password</Label>
            <Input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new-password">New Password</Label>
            <ValidatedInput
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              onBlur={newPasswordValidation.handleBlur}
              validation={newPasswordValidation.validation}
              touched={newPasswordValidation.touched}
            />
            <ValidationMessage
              validation={newPasswordValidation.validation}
              touched={newPasswordValidation.touched}
            />
            <PasswordStrength password={newPassword} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm-password">Confirm New Password</Label>
            <ValidatedInput
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              onBlur={confirmPasswordValidation.handleBlur}
              validation={confirmPasswordValidation.validation}
              touched={confirmPasswordValidation.touched}
            />
            <ValidationMessage
              validation={confirmPasswordValidation.validation}
              touched={confirmPasswordValidation.touched}
            />
          </div>

          <Button onClick={handlePasswordChange} disabled={loading} className="w-full">
            <Lock className="w-4 h-4 mr-2" />
            {loading ? 'Changing...' : 'Change Password'}
          </Button>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            <CardTitle>Notification Settings</CardTitle>
          </div>
          <CardDescription>Manage how you receive notifications</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900 dark:text-slate-100">Email Notifications</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">Receive email updates about your documents</p>
            </div>
            <Switch
              checked={emailNotifications}
              onCheckedChange={setEmailNotifications}
            />
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900 dark:text-slate-100">Push Notifications</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">Receive push notifications in browser</p>
            </div>
            <Switch
              checked={pushNotifications}
              onCheckedChange={setPushNotifications}
            />
          </div>

          <Button onClick={handleNotificationSave} disabled={loading} className="w-full">
            <Save className="w-4 h-4 mr-2" />
            {loading ? 'Saving...' : 'Save Notification Settings'}
          </Button>
        </CardContent>
      </Card>

      {/* Security Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            <CardTitle>Security</CardTitle>
          </div>
          <CardDescription>Additional security options</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Last login: {new Date().toLocaleDateString()} at {new Date().toLocaleTimeString()}
            </p>
          </div>
          <Button variant="outline" className="w-full">
            <Shield className="w-4 h-4 mr-2" />
            View Login History
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
