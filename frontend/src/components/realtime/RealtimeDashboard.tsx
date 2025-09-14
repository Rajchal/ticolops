import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Activity, Users, GitBranch, Zap, AlertTriangle, Lightbulb } from 'lucide-react';
import { ActivityFeed } from './ActivityFeed';
import { TeamPresence } from './TeamPresence';
import { ConflictAlerts } from './ConflictAlerts';
import { CollaborationSuggestions } from './CollaborationSuggestions';
import { ConnectionStatus } from './ConnectionStatus';
import { useRealtime } from '../../contexts/RealtimeContext';

interface RealtimeDashboardProps {
  layout?: 'grid' | 'sidebar' | 'compact';
  showStats?: boolean;
  maxItems?: {
    activities?: number;
    presence?: number;
    conflicts?: number;
    suggestions?: number;
  };
}

export const RealtimeDashboard: React.FC<RealtimeDashboardProps> = ({
  layout = 'grid',
  showStats = true,
  maxItems = {
    activities: 8,
    presence: 8,
    conflicts: 3,
    suggestions: 3,
  }
}) => {
  const { userPresence, activities, conflicts, isConnected } = useRealtime();
  
  const onlineCount = userPresence.filter(user => user.status === 'online' || user.status === 'busy').length;
  const recentActivitiesCount = activities.filter(
    activity => new Date(activity.timestamp) > new Date(Date.now() - 60 * 60 * 1000) // Last hour
  ).length;
  const highPriorityConflicts = conflicts.filter(c => c.severity === 'high').length;

  const StatsCards = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Team Online</CardTitle>
          <Users className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{onlineCount}</div>
          <p className="text-xs text-muted-foreground">
            of {userPresence.length} total members
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{recentActivitiesCount}</div>
          <p className="text-xs text-muted-foreground">
            events in the last hour
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Active Conflicts</CardTitle>
          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{conflicts.length}</div>
          <p className="text-xs text-muted-foreground">
            {highPriorityConflicts > 0 ? `${highPriorityConflicts} high priority` : 'all resolved'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Connection</CardTitle>
          <Zap className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {isConnected ? 'Live' : 'Off'}
          </div>
          <p className="text-xs text-muted-foreground">
            <ConnectionStatus showText />
          </p>
        </CardContent>
      </Card>
    </div>
  );

  if (layout === 'compact') {
    return (
      <div className="space-y-4">
        {showStats && <StatsCards />}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ActivityFeed maxItems={maxItems.activities} />
          <TeamPresence maxUsers={maxItems.presence} />
        </div>
        {conflicts.length > 0 && (
          <ConflictAlerts maxAlerts={maxItems.conflicts} />
        )}
      </div>
    );
  }

  if (layout === 'sidebar') {
    return (
      <div className="flex gap-6">
        <div className="flex-1 space-y-6">
          {showStats && <StatsCards />}
          <ActivityFeed maxItems={maxItems.activities} />
          {conflicts.length > 0 && (
            <ConflictAlerts maxAlerts={maxItems.conflicts} />
          )}
        </div>
        <div className="w-80 space-y-6">
          <TeamPresence maxUsers={maxItems.presence} />
          <CollaborationSuggestions maxSuggestions={maxItems.suggestions} />
        </div>
      </div>
    );
  }

  // Default grid layout
  return (
    <div className="space-y-6">
      {showStats && <StatsCards />}
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ActivityFeed maxItems={maxItems.activities} />
        <TeamPresence maxUsers={maxItems.presence} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {conflicts.length > 0 && (
          <ConflictAlerts maxAlerts={maxItems.conflicts} />
        )}
        <CollaborationSuggestions maxSuggestions={maxItems.suggestions} />
      </div>
    </div>
  );
};