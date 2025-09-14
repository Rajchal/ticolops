import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Circle, User, FileText, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { useRealtime } from '../../contexts/RealtimeContext';
import type { UserPresence } from '../../services/websocketService';

const getStatusColor = (status: UserPresence['status']) => {
  switch (status) {
    case 'online':
      return 'text-green-500';
    case 'away':
      return 'text-yellow-500';
    case 'busy':
      return 'text-red-500';
    case 'offline':
      return 'text-gray-400';
    default:
      return 'text-gray-400';
  }
};

const getStatusText = (status: UserPresence['status']) => {
  switch (status) {
    case 'online':
      return 'Online';
    case 'away':
      return 'Away';
    case 'busy':
      return 'Busy';
    case 'offline':
      return 'Offline';
    default:
      return 'Unknown';
  }
};

interface PresenceItemProps {
  user: UserPresence;
}

const PresenceItem: React.FC<PresenceItemProps> = ({ user }) => {
  return (
    <div className="flex items-center space-x-3 p-3 rounded-md hover:bg-accent/50 transition-colors">
      <div className="relative">
        {user.userAvatar ? (
          <img
            src={user.userAvatar}
            alt={user.userName}
            className="h-10 w-10 rounded-full"
          />
        ) : (
          <div className="h-10 w-10 rounded-full bg-primary flex items-center justify-center">
            <User className="h-5 w-5 text-primary-foreground" />
          </div>
        )}
        <div className={`absolute -bottom-1 -right-1 h-4 w-4 rounded-full border-2 border-background flex items-center justify-center ${getStatusColor(user.status)}`}>
          <Circle className="h-2 w-2 fill-current" />
        </div>
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-foreground truncate">
            {user.userName}
          </span>
          <span className={`text-xs ${getStatusColor(user.status)}`}>
            {getStatusText(user.status)}
          </span>
        </div>
        
        {user.currentProject && (
          <div className="flex items-center space-x-1 mt-1">
            <FileText className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs text-muted-foreground truncate">
              Working on {user.currentProject}
            </span>
          </div>
        )}
        
        {user.currentFile && (
          <div className="flex items-center space-x-1 mt-1">
            <FileText className="h-3 w-3 text-muted-foreground" />
            <span className="text-xs text-muted-foreground truncate">
              Editing {user.currentFile}
            </span>
          </div>
        )}
        
        <div className="flex items-center space-x-1 mt-1">
          <Clock className="h-3 w-3 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">
            {user.status === 'offline' 
              ? `Last seen ${formatDistanceToNow(new Date(user.lastSeen), { addSuffix: true })}`
              : 'Active now'
            }
          </span>
        </div>
      </div>
    </div>
  );
};

interface TeamPresenceProps {
  showHeader?: boolean;
  maxUsers?: number;
}

export const TeamPresence: React.FC<TeamPresenceProps> = ({ 
  showHeader = true, 
  maxUsers = 10 
}) => {
  const { userPresence, isConnected } = useRealtime();

  // Sort users by status priority and then by name
  const sortedUsers = [...userPresence]
    .sort((a, b) => {
      const statusPriority = { online: 0, busy: 1, away: 2, offline: 3 };
      const aPriority = statusPriority[a.status] ?? 4;
      const bPriority = statusPriority[b.status] ?? 4;
      
      if (aPriority !== bPriority) {
        return aPriority - bPriority;
      }
      
      return a.userName.localeCompare(b.userName);
    })
    .slice(0, maxUsers);

  const onlineCount = userPresence.filter(user => user.status === 'online' || user.status === 'busy').length;

  if (showHeader) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Team Presence</span>
            <div className="flex items-center space-x-2">
              <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm font-normal text-muted-foreground">
                {onlineCount} online
              </span>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {sortedUsers.length > 0 ? (
              sortedUsers.map((user) => (
                <PresenceItem key={user.userId} user={user} />
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <User className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No team members online</p>
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
    <div className="space-y-2">
      {sortedUsers.length > 0 ? (
        sortedUsers.map((user) => (
          <PresenceItem key={user.userId} user={user} />
        ))
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          <User className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No team members online</p>
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