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

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setIsAuthenticated(Boolean(localStorage.getItem('access_token')));
    setLoading(false);
  }, []);

  if (loading) return <div className="min-h-screen flex items-center justify-center"><Skeleton className="h-8 w-32" /></div>;

  return (
    <ErrorBoundary>
      <ToastContainer />
      <SpeedInsights />
      <Routes>
        <Route path="/login" element={isAuthenticated ? <Navigate to="/admin/dashboard" replace /> : <Login onLogin={() => setIsAuthenticated(true)} />} />
        <Route path="/admin/*" element={isAuthenticated ? <AdminLayout /> : <Navigate to="/login" replace />}>
          <Route path="dashboard" element={<PersonalDashboard />} />
          <Route path="workspace" element={<WorkspaceReview />} />
          <Route path="" element={<Navigate to="dashboard" replace />} />
        </Route>
        <Route path="/" element={<Navigate to={isAuthenticated ? '/admin/dashboard' : '/login'} replace />} />
        <Route path="*" element={<Navigate to={isAuthenticated ? '/admin/dashboard' : '/login'} replace />} />
      </Routes>
    </ErrorBoundary>
  );
}
