import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { 
  Bell, 
  CheckCircle, 
  AlertCircle, 
  Users, 
  GitCommit, 
  MessageSquare,
  Zap,
  X,
  Eye,
  EyeOff,
  ExternalLink
} from 'lucide-react';
import { Button } from '../ui/Button';

export interface Notification {
  id: string;
  type: 'activity' | 'deployment' | 'mention' | 'conflict' | 'system';
  title: string;
  message: string;
  isRead: boolean;
  priority: 'low' | 'medium' | 'high';
  userId: string;
  projectId?: string;
  projectName?: string;
  repositoryId?: string;
  repositoryName?: string;
  actionUrl?: string;
  actionText?: string;
  createdAt: Date;
  readAt?: Date;
  metadata?: Record<string, any>;
}

interface NotificationCardProps {
  notification: Notification;
  onMarkAsRead?: (notification: Notification) => void;
  onMarkAsUnread?: (notification: Notification) => void;
  onDismiss?: (notification: Notification) => void;
  onAction?: (notification: Notification) => void;
  compact?: boolean;
  showActions?: boolean;
}

const getNotificationIcon = (type: Notification['type']) => {
  switch (type) {
    case 'activity':
      return <Users className="h-4 w-4 text-blue-500" />;
    case 'deployment':
      return <Zap className="h-4 w-4 text-green-500" />;
    case 'mention':
      return <MessageSquare className="h-4 w-4 text-purple-500" />;
    case 'conflict':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    case 'system':
      return <Bell className="h-4 w-4 text-gray-500" />;
    default:
      return <Bell className="h-4 w-4 text-gray-500" />;
  }
};

const getPriorityColor = (priority: Notification['priority']) => {
  switch (priority) {
    case 'high':
      return 'border-l-red-500 bg-red-50';
    case 'medium':
      return 'border-l-yellow-500 bg-yellow-50';
    case 'low':
      return 'border-l-blue-500 bg-blue-50';
    default:
      return 'border-l-gray-500 bg-gray-50';
  }
};

const getPriorityDot = (priority: Notification['priority']) => {
  switch (priority) {
    case 'high':
      return 'bg-red-500';
    case 'medium':
      return 'bg-yellow-500';
    case 'low':
      return 'bg-blue-500';
    default:
      return 'bg-gray-500';
  }
};

export const NotificationCard: React.FC<NotificationCardProps> = ({
  notification,
  onMarkAsRead,
  onMarkAsUnread,
  onDismiss,
  onAction,
  compact = false,
  showActions = true,
}) => {
  if (compact) {
    return (
      <div className={`flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors ${
        !notification.isRead ? 'bg-blue-50' : ''
      }`}>
        <div className="flex-shrink-0">
          {getNotificationIcon(notification.type)}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            {!notification.isRead && (
              <div className={`w-2 h-2 rounded-full ${getPriorityDot(notification.priority)}`} />
            )}
            <p className="text-sm font-medium text-foreground truncate">
              {notification.title}
            </p>
          </div>
          <p className="text-xs text-muted-foreground truncate">
            {notification.message}
          </p>
          <p className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(notification.createdAt), { addSuffix: true })}
          </p>
        </div>
        
        {showActions && (
          <div className="flex items-center space-x-1">
            {notification.actionUrl && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAction?.(notification)}
                className="h-6 px-2 text-xs"
              >
                <ExternalLink className="h-3 w-3" />
              </Button>
            )}
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => onDismiss?.(notification)}
              className="h-6 w-6 p-0"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`border-l-4 rounded-r-lg p-4 ${getPriorityColor(notification.priority)} ${
      !notification.isRead ? 'shadow-sm' : ''
    }`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <div className="flex-shrink-0 mt-1">
            {getNotificationIcon(notification.type)}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              {!notification.isRead && (
                <div className={`w-2 h-2 rounded-full ${getPriorityDot(notification.priority)}`} />
              )}
              <h4 className="text-sm font-semibold text-gray-900">
                {notification.title}
              </h4>
              <span className="text-xs text-gray-500 capitalize">
                {notification.priority} priority
              </span>
            </div>
            
            <p className="text-sm text-gray-700 mb-2">
              {notification.message}
            </p>
            
            <div className="flex items-center space-x-4 text-xs text-gray-600">
              <span>
                {formatDistanceToNow(new Date(notification.createdAt), { addSuffix: true })}
              </span>
              
              {notification.projectName && (
                <span className="flex items-center space-x-1">
                  <span>Project:</span>
                  <span className="font-medium">{notification.projectName}</span>
                </span>
              )}
              
              {notification.repositoryName && (
                <span className="flex items-center space-x-1">
                  <GitCommit className="h-3 w-3" />
                  <span>{notification.repositoryName}</span>
                </span>
              )}
            </div>
            
            {notification.readAt && (
              <p className="text-xs text-gray-500 mt-1">
                Read {formatDistanceToNow(new Date(notification.readAt), { addSuffix: true })}
              </p>
            )}
          </div>
        </div>
        
        {showActions && (
          <div className="flex items-center space-x-2 ml-4">
            {notification.isRead ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onMarkAsUnread?.(notification)}
                className="text-xs"
                title="Mark as unread"
              >
                <EyeOff className="h-3 w-3" />
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onMarkAsRead?.(notification)}
                className="text-xs"
                title="Mark as read"
              >
                <Eye className="h-3 w-3" />
              </Button>
            )}
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => onDismiss?.(notification)}
              className="text-xs"
              title="Dismiss"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>
      
      {notification.actionUrl && notification.actionText && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onAction?.(notification)}
            className="text-xs"
          >
            <ExternalLink className="h-3 w-3 mr-1" />
            {notification.actionText}
          </Button>
        </div>
      )}
    </div>
  );
};