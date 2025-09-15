import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { RealtimeProvider } from './contexts/RealtimeContext';
import { NotificationProvider } from './contexts/NotificationContext';
import { LoginForm } from './components/auth/LoginForm';
import { RegisterForm } from './components/auth/RegisterForm';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { Activity } from './pages/Activity';
import { Projects } from './pages/Projects';
import { ProjectDetail } from './pages/ProjectDetail';
import { Deployments } from './pages/Deployments';
import { Notifications } from './pages/Notifications';
import '@fontsource/inter/400.css'; // regular
import '@fontsource/inter/700.css'; // bold





const queryClient = new QueryClient();

const AppRoutes: React.FC = () => {
  const { user } = useAuth();

  return (
    <Routes>
      <Route 
        path="/login" 
        element={user ? <Navigate to="/" replace /> : <LoginForm />} 
      />
      <Route 
        path="/register" 
        element={user ? <Navigate to="/" replace /> : <RegisterForm />} 
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="projects" element={<Projects />} />
        <Route path="projects/:projectId" element={<ProjectDetail />} />
        <Route path="activity" element={<Activity />} />
        <Route path="deployments" element={<Deployments />} />
        <Route path="repositories" element={<div>Repositories Page</div>} />
        <Route path="team" element={<div>Team Page</div>} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="settings" element={<div>Settings Page</div>} />
        <Route path="profile" element={<div>Profile Page</div>} />
      </Route>
    </Routes>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AuthProvider>
          <RealtimeProvider>
            <NotificationProvider>
              <AppRoutes />
            </NotificationProvider>
          </RealtimeProvider>
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
