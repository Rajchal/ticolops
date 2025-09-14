import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Activity, Users, GitBranch, Zap, Grid, Sidebar, Maximize2 } from 'lucide-react';
import { RealtimeDashboard } from '../components/realtime/RealtimeDashboard';
import { ConnectionStatus } from '../components/realtime/ConnectionStatus';
import { DeploymentStatusWidget } from '../components/deployments/DeploymentStatusWidget';
import { useRealtime } from '../contexts/RealtimeContext';
import { useNavigate } from 'react-router-dom';

export const Dashboard: React.FC = () => {
  const { userPresence } = useRealtime();
  const navigate = useNavigate();
  const [dashboardLayout, setDashboardLayout] = useState<'grid' | 'sidebar' | 'compact'>('grid');
  
  const onlineCount = userPresence.filter(user => user.status === 'online' || user.status === 'busy').length;

  // Mock deployment data - in a real app, this would come from an API
  const mockDeployments = [
    {
      id: '1',
      repositoryId: 'repo-1',
      repositoryName: 'ecommerce-frontend',
      projectId: 'project-1',
      projectName: 'E-commerce Platform',
      branch: 'main',
      commitHash: 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0',
      commitMessage: 'Add shopping cart functionality',
      author: 'John Doe',
      status: 'success' as const,
      url: 'https://ecommerce-frontend-abc123.vercel.app',
      previewUrl: 'https://ecommerce-frontend-abc123.vercel.app',
      buildDuration: 145,
      startedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
      completedAt: new Date(Date.now() - 2 * 60 * 60 * 1000 + 145 * 1000),
      logs: [],
      buildCommand: 'npm run build',
      environment: 'production' as const,
    },
    {
      id: '2',
      repositoryId: 'repo-2',
      repositoryName: 'task-manager-app',
      projectId: 'project-2',
      projectName: 'Task Management App',
      branch: 'develop',
      commitHash: 'b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1',
      commitMessage: 'Update API endpoints',
      author: 'Jane Smith',
      status: 'building' as const,
      buildDuration: 67,
      startedAt: new Date(Date.now() - 5 * 60 * 1000),
      logs: [],
      buildCommand: 'npm run build',
      environment: 'staging' as const,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome to Ticolops - Track, Collaborate, Deploy, Succeed
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Button
              variant={dashboardLayout === 'grid' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setDashboardLayout('grid')}
            >
              <Grid className="h-4 w-4" />
            </Button>
            <Button
              variant={dashboardLayout === 'sidebar' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setDashboardLayout('sidebar')}
            >
              <Sidebar className="h-4 w-4" />
            </Button>
            <Button
              variant={dashboardLayout === 'compact' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setDashboardLayout('compact')}
            >
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
          <ConnectionStatus showText />
        </div>
      </div>

      {/* Project Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Projects</CardTitle>
            <GitBranch className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <p className="text-xs text-muted-foreground">
              +1 from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Team Members</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">
              +2 new this week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Deployments</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">24</div>
            <p className="text-xs text-muted-foreground">
              +8 this week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Now</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{onlineCount}</div>
            <p className="text-xs text-muted-foreground">
              Team members online
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Dashboard Content */}
      {dashboardLayout === 'sidebar' ? (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-3">
            <RealtimeDashboard 
              layout={dashboardLayout}
              showStats={false}
              maxItems={{
                activities: 10,
                presence: 12,
                conflicts: 5,
                suggestions: 4,
              }}
            />
          </div>
          <div className="space-y-6">
            <DeploymentStatusWidget
              deployments={mockDeployments}
              onViewAll={() => navigate('/deployments')}
              onViewPreview={(deployment) => window.open(deployment.url || deployment.previewUrl, '_blank')}
              maxItems={3}
            />
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <RealtimeDashboard 
                layout={dashboardLayout}
                showStats={true}
                maxItems={{
                  activities: 8,
                  presence: 10,
                  conflicts: 3,
                  suggestions: 3,
                }}
              />
            </div>
            <div>
              <DeploymentStatusWidget
                deployments={mockDeployments}
                onViewAll={() => navigate('/deployments')}
                onViewPreview={(deployment) => window.open(deployment.url || deployment.previewUrl, '_blank')}
                maxItems={5}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};