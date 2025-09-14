import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { GitCommit, Zap, Users, AlertTriangle, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { useRealtime } from '../../contexts/RealtimeContext';
import type { ActivityEvent } from '../../services/websocketService';

const getActivityIcon = (type: ActivityEvent['type']) => {
  switch (type) {
    case 'commit':
      return <GitCommit className="h-4 w-4 text-blue-500" />;
    case 'deployment':
      return <Zap className="h-4 w-4 text-green-500" />;
    case 'collaboration':
      return <Users className="h-4 w-4 text-purple-500" />;
    case 'conflict':
      return <AlertTriangle className="h-4 w-4 text-red-500" />;
    case 'presence':
      return <Clock className="h-4 w-4 text-gray-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-500" />;
  }
};

const getActivityColor = (type: ActivityEvent['type']) => {
  switch (type) {
    case 'commit':
      return 'border-l-blue-500';
    case 'deployment':
      return 'border-l-green-500';
    case 'collaboration':
      return 'border-l-purple-500';
    case 'conflict':
      return 'border-l-red-500';
    case 'presence':
      return 'border-l-gray-500';
    default:
      return 'border-l-gray-500';
  }
};

interface ActivityItemProps {
  activity: ActivityEvent;
}

const ActivityItem: React.FC<ActivityItemProps> = ({ activity }) => {
  return (
    <div className={`flex items-start space-x-3 p-3 border-l-4 ${getActivityColor(activity.type)} bg-card rounded-r-md`}>
      <div className="flex-shrink-0 mt-1">
        {getActivityIcon(activity.type)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2">
          {activity.userAvatar ? (
            <img
              src={activity.userAvatar}
              alt={activity.userName}
              className="h-6 w-6 rounded-full"
            />
          ) : (
            <div className="h-6 w-6 rounded-full bg-primary flex items-center justify-center">
              <span className="text-xs font-medium text-primary-foreground">
                {activity.userName.charAt(0).toUpperCase()}
              </span>
            </div>
          )}
          <span className="text-sm font-medium text-foreground">
            {activity.userName}
          </span>
          <span className="text-xs text-muted-foreground">
            in {activity.projectName}
          </span>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          {activity.message}
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
        </p>
      </div>
    </div>
  );
};

interface ActivityFeedProps {
  maxItems?: number;
  showHeader?: boolean;
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({ 
  maxItems = 10, 
  showHeader = true 
}) => {
  const { activities, isConnected } = useRealtime();

  const displayedActivities = activities.slice(0, maxItems);

  if (showHeader) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <span>Recent Activity</span>
            <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {displayedActivities.length > 0 ? (
              displayedActivities.map((activity) => (
                <ActivityItem key={activity.id} activity={activity} />
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No recent activity</p>
                {!isConnected && (
                  <p className="text-xs mt-1 text-red-500">
                    Disconnected - trying to reconnect...
                  </p>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {displayedActivities.length > 0 ? (
        displayedActivities.map((activity) => (
          <ActivityItem key={activity.id} activity={activity} />
        ))
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No recent activity</p>
          {!isConnected && (
            <p className="text-xs mt-1 text-red-500">
              Disconnected - trying to reconnect...
            </p>
          )}
        </div>
      )}
    </div>
  );
};