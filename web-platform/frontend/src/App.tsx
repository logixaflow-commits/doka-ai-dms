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
import {
  getCurrentUser,
  isSupabaseConfigured,
  signOut,
  type SupabaseUser,
} from '@/lib/supabaseAuth';

export default function App() {
  const [user, setUser] = useState<SupabaseUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function restoreAuth() {
      if (!isSupabaseConfigured()) {
        if (mounted) setLoading(false);
        return;
      }

      const currentUser = await getCurrentUser();
      if (mounted) {
        setUser(currentUser);
        setLoading(false);
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
          element={isAuthenticated ? <Navigate to="/admin/dashboard" replace /> : <Login onLogin={async () => setUser(await getCurrentUser())} />}
        />
        <Route path="/admin/*" element={isAuthenticated ? <AdminLayout /> : <Navigate to="/login" replace />}>
          <Route path="dashboard" element={<PersonalDashboard />} />
          <Route path="workspace" element={<WorkspaceReview />} />
          <Route path="cloud-documents" element={<CloudDocuments />} />
          <Route path="" element={<Navigate to="dashboard" replace />} />
        </Route>
        <Route path="/" element={<Navigate to={isAuthenticated ? '/admin/dashboard' : '/login'} replace />} />
        <Route path="*" element={<Navigate to={isAuthenticated ? '/admin/dashboard' : '/login'} replace />} />
      </Routes>
    </ErrorBoundary>
  );
}
