import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router';
import { SpeedInsights } from '@vercel/speed-insights/react';
import { Skeleton } from '@/components/ui/skeleton';
import Login from '@/components/Login';
import ErrorBoundary from '@/components/ErrorBoundary';
import ToastContainer from '@/components/Toast';
import AdminLayout from '@/layouts/AdminLayout';
import PersonalDashboard from '@/pages/PersonalDashboard';
import WorkspaceReview from '@/pages/WorkspaceReview';
import CloudDocuments from '@/pages/CloudDocuments';
import CloudAudit from '@/pages/CloudAudit';
import {
  getCurrentUser,
  isSupabaseConfigured,
  type SupabaseUser,
} from '@/lib/supabaseAuth';
import { getLocalCurrentUser, isLocalAuthEnabled } from '@/lib/localAuth';

export default function App() {
  const [user, setUser] = useState<SupabaseUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function restoreAuth() {
      if (!isSupabaseConfigured() && !isLocalAuthEnabled()) {
        if (mounted) setLoading(false);
        return;
      }

      try {
        const currentUser = isLocalAuthEnabled()
          ? await getLocalCurrentUser()
          : await getCurrentUser();
        if (mounted) {
          setUser(currentUser);
          setLoading(false);
        }
      } catch {
        if (mounted) {
          setUser(null);
          setLoading(false);
        }
      }
    }

    restoreAuth();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Skeleton className="h-8 w-32" /></div>;

  const isAuthenticated = Boolean(user);

  return (
    <ErrorBoundary>
      <ToastContainer />
      <SpeedInsights />
      <Routes>
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to={isLocalAuthEnabled() ? '/admin/workspace' : '/admin/dashboard'} replace /> : <Login onLogin={async () => setUser(isLocalAuthEnabled() ? await getLocalCurrentUser() : await getCurrentUser())} />}
        />
        <Route path="/admin/*" element={isAuthenticated ? <AdminLayout /> : <Navigate to="/login" replace />}>
          <Route path="dashboard" element={<PersonalDashboard />} />
          <Route path="workspace" element={<WorkspaceReview />} />
          <Route path="cloud-documents" element={<CloudDocuments />} />
          <Route path="activity" element={<CloudAudit />} />
          <Route path="" element={<Navigate to={isLocalAuthEnabled() ? 'workspace' : 'dashboard'} replace />} />
        </Route>
        <Route path="/" element={<Navigate to={isAuthenticated ? (isLocalAuthEnabled() ? '/admin/workspace' : '/admin/dashboard') : '/login'} replace />} />
        <Route path="*" element={<Navigate to={isAuthenticated ? (isLocalAuthEnabled() ? '/admin/workspace' : '/admin/dashboard') : '/login'} replace />} />
      </Routes>
    </ErrorBoundary>
  );
}
