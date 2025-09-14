import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Activity, Users, GitBranch, Zap, Grid, Sidebar, Maximize2 } from 'lucide-react';
import { RealtimeDashboard } from '../components/realtime/RealtimeDashboard';
import { ConnectionStatus } from '../components/realtime/ConnectionStatus';
import { useRealtime } from '../contexts/RealtimeContext';

export const Dashboard: React.FC = () => {
  const { userPresence } = useRealtime();
  const [dashboardLayout, setDashboardLayout] = useState<'grid' | 'sidebar' | 'compact'>('grid');
  
  const onlineCount = userPresence.filter(user => user.status === 'online' || user.status === 'busy').length;

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

      {/* Real-time Collaboration Dashboard */}
      <RealtimeDashboard 
        layout={dashboardLayout}
        showStats={true}
        maxItems={{
          activities: 10,
          presence: 12,
          conflicts: 5,
          suggestions: 4,
        }}
      />
    </div>
  );
};