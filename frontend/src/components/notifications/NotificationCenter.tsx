import React, { useState, useEffect } from 'react';
import { 
  Bell, 
  Settings, 
  Filter, 
  Search, 
  CheckCircle, 
  Trash2,
  RefreshCw,
  X
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { NotificationCard, type Notification } from './NotificationCard';

interface NotificationCenterProps {
  isOpen: boolean;
  onClose: () => void;
  notifications: Notification[];
  onMarkAsRead?: (notification: Notification) => void;
  onMarkAsUnread?: (notification: Notification) => void;
  onMarkAllAsRead?: () => void;
  onDismiss?: (notification: Notification) => void;
  onClearAll?: () => void;
  onRefresh?: () => void;
  onOpenSettings?: () => void;
  isLoading?: boolean;
}

type FilterType = 'all' | 'unread' | 'activity' | 'deployment' | 'mention' | 'conflict' | 'system';
type SortType = 'newest' | 'oldest' | 'priority';

export const NotificationCenter: React.FC<NotificationCenterProps> = ({
  isOpen,
  onClose,
  notifications,
  onMarkAsRead,
  onMarkAsUnread,
  onMarkAllAsRead,
  onDismiss,
  onClearAll,
  onRefresh,
  onOpenSettings,
  isLoading = false,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<FilterType>('all');
  const [sort, setSort] = useState<SortType>('newest');

  // Filter and sort notifications
  const filteredNotifications = notifications
    .filter(notification => {
      // Apply search filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        return (
          notification.title.toLowerCase().includes(query) ||
          notification.message.toLowerCase().includes(query) ||
          notification.projectName?.toLowerCase().includes(query) ||
          notification.repositoryName?.toLowerCase().includes(query)
        );
      }
      return true;
    })
    .filter(notification => {
      // Apply type filter
      switch (filter) {
        case 'unread':
          return !notification.isRead;
        case 'activity':
        case 'deployment':
        case 'mention':
        case 'conflict':
        case 'system':
          return notification.type === filter;
        default:
          return true;
      }
    })
    .sort((a, b) => {
      // Apply sorting
      switch (sort) {
        case 'oldest':
          return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        case 'priority':
          const priorityOrder = { high: 0, medium: 1, low: 2 };
          const aPriority = priorityOrder[a.priority];
          const bPriority = priorityOrder[b.priority];
          if (aPriority !== bPriority) {
            return aPriority - bPriority;
          }
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
        case 'newest':
        default:
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      }
    });

  const unreadCount = notifications.filter(n => !n.isRead).length;
  const highPriorityCount = notifications.filter(n => n.priority === 'high' && !n.isRead).length;

  const handleAction = (notification: Notification) => {
    if (notification.actionUrl) {
      window.open(notification.actionUrl, '_blank');
      // Mark as read when action is taken
      if (!notification.isRead) {
        onMarkAsRead?.(notification);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-4xl h-[80vh] flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 border-b">
          <div>
            <CardTitle className="text-xl font-semibold flex items-center space-x-2">
              <Bell className="h-5 w-5" />
              <span>Notifications</span>
              {unreadCount > 0 && (
                <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                  {unreadCount}
                </span>
              )}
            </CardTitle>
            {highPriorityCount > 0 && (
              <p className="text-sm text-red-600 mt-1">
                {highPriorityCount} high priority notification{highPriorityCount > 1 ? 's' : ''}
              </p>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        
        <CardContent className="flex-1 flex flex-col p-0">
          {/* Controls */}
          <div className="flex items-center justify-between p-4 border-b bg-gray-50">
            <div className="flex items-center space-x-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  type="text"
                  placeholder="Search notifications..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>
              
              <div className="flex items-center space-x-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value as FilterType)}
                  className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                >
                  <option value="all">All</option>
                  <option value="unread">Unread</option>
                  <option value="activity">Activity</option>
                  <option value="deployment">Deployment</option>
                  <option value="mention">Mentions</option>
                  <option value="conflict">Conflicts</option>
                  <option value="system">System</option>
                </select>
              </div>
              
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortType)}
                className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
                <option value="priority">Priority</option>
              </select>
              
              <div className="text-sm text-muted-foreground">
                {filteredNotifications.length} of {notifications.length}
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onRefresh}
                disabled={isLoading}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              
              {unreadCount > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onMarkAllAsRead}
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Mark All Read
                </Button>
              )}
              
              <Button
                variant="outline"
                size="sm"
                onClick={onOpenSettings}
              >
                <Settings className="h-4 w-4 mr-2" />
                Settings
              </Button>
              
              {notifications.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onClearAll}
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Clear All
                </Button>
              )}
            </div>
          </div>

          {/* Notifications List */}
          <div className="flex-1 overflow-auto">
            {filteredNotifications.length === 0 ? (
              <div className="flex items-center justify-center h-full text-center">
                <div>
                  <Bell className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  {searchQuery || filter !== 'all' ? (
                    <>
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No notifications found</h3>
                      <p className="text-gray-500">Try adjusting your search or filters</p>
                    </>
                  ) : (
                    <>
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No notifications yet</h3>
                      <p className="text-gray-500">You'll see notifications about team activities here</p>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-4 space-y-3">
                {filteredNotifications.map((notification) => (
                  <NotificationCard
                    key={notification.id}
                    notification={notification}
                    onMarkAsRead={onMarkAsRead}
                    onMarkAsUnread={onMarkAsUnread}
                    onDismiss={onDismiss}
                    onAction={handleAction}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Status Bar */}
          <div className="flex items-center justify-between p-3 border-t bg-gray-50 text-sm text-muted-foreground">
            <div className="flex items-center space-x-4">
              <span>Total: {notifications.length}</span>
              <span>Unread: {unreadCount}</span>
              {highPriorityCount > 0 && (
                <span className="text-red-600">High Priority: {highPriorityCount}</span>
              )}
            </div>
            
            <div className="flex items-center space-x-2">
              {isLoading && (
                <div className="flex items-center space-x-2">
                  <RefreshCw className="h-3 w-3 animate-spin" />
                  <span>Updating...</span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};