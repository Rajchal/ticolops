import React, { useState, useEffect } from 'react';
import { Bell, Settings, RefreshCw, CheckCircle, Trash2 } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { NotificationCenter } from '../components/notifications/NotificationCenter';
import { NotificationSettings } from '../components/notifications/NotificationSettings';
import { useAuth } from '../contexts/AuthContext';
import type { Notification } from '../components/notifications/NotificationCard';

// Mock data - in a real app, this would come from an API
const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'deployment',
    title: 'Deployment Successful',
    message: 'Your ecommerce-frontend has been successfully deployed to production.',
    isRead: false,
    priority: 'medium',
    userId: 'user-1',
    projectId: 'project-1',
    projectName: 'E-commerce Platform',
    repositoryId: 'repo-1',
    repositoryName: 'ecommerce-frontend',
    actionUrl: 'https://ecommerce-frontend.vercel.app',
    actionText: 'View Deployment',
    createdAt: new Date(Date.now() - 5 * 60 * 1000), // 5 minutes ago
  },
  {
    id: '2',
    type: 'mention',
    title: 'You were mentioned',
    message: 'Sarah Chen mentioned you in a comment: "Hey @john, can you review the authentication flow?"',
    isRead: false,
    priority: 'high',
    userId: 'user-1',
    projectId: 'project-1',
    projectName: 'E-commerce Platform',
    actionUrl: '/projects/project-1#comment-123',
    actionText: 'View Comment',
    createdAt: new Date(Date.now() - 15 * 60 * 1000), // 15 minutes ago
  },
  {
    id: '3',
    type: 'conflict',
    title: 'Merge Conflict Detected',
    message: 'A merge conflict was detected in the user authentication module. Multiple team members are working on the same files.',
    isRead: false,
    priority: 'high',
    userId: 'user-1',
    projectId: 'project-1',
    projectName: 'E-commerce Platform',
    repositoryId: 'repo-1',
    repositoryName: 'ecommerce-frontend',
    actionUrl: '/projects/project-1/conflicts',
    actionText: 'Resolve Conflict',
    createdAt: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
  },
  {
    id: '4',
    type: 'activity',
    title: 'Team Member Started Working',
    message: 'Mike Johnson started working on the shopping cart component you\'re interested in.',
    isRead: true,
    priority: 'low',
    userId: 'user-1',
    projectId: 'project-1',
    projectName: 'E-commerce Platform',
    readAt: new Date(Date.now() - 45 * 60 * 1000),
    createdAt: new Date(Date.now() - 60 * 60 * 1000), // 1 hour ago
  },
  {
    id: '5',
    type: 'deployment',
    title: 'Deployment Failed',
    message: 'The deployment of task-manager-backend failed due to build errors. Check the logs for more details.',
    isRead: true,
    priority: 'high',
    userId: 'user-1',
    projectId: 'project-2',
    projectName: 'Task Management App',
    repositoryId: 'repo-2',
    repositoryName: 'task-manager-backend',
    actionUrl: '/deployments/deployment-123/logs',
    actionText: 'View Logs',
    readAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
  },
  {
    id: '6',
    type: 'system',
    title: 'System Maintenance',
    message: 'Scheduled maintenance will occur tonight from 2:00 AM to 4:00 AM UTC. Some features may be temporarily unavailable.',
    isRead: true,
    priority: 'medium',
    userId: 'user-1',
    readAt: new Date(Date.now() - 4 * 60 * 60 * 1000),
    createdAt: new Date(Date.now() - 4 * 60 * 60 * 1000), // 4 hours ago
  },
];

const mockProjects = [
  { id: 'project-1', name: 'E-commerce Platform' },
  { id: 'project-2', name: 'Task Management App' },
  { id: 'project-3', name: 'Blog Platform' },
];

const defaultPreferences = {
  email: {
    enabled: true,
    activity: false,
    deployment: true,
    mentions: true,
    conflicts: true,
    system: false,
    digest: 'daily' as const,
  },
  inApp: {
    enabled: true,
    activity: true,
    deployment: true,
    mentions: true,
    conflicts: true,
    system: true,
    sound: true,
  },
  push: {
    enabled: false,
    activity: false,
    deployment: true,
    mentions: true,
    conflicts: true,
    system: false,
  },
  quietHours: {
    enabled: false,
    startTime: '22:00',
    endTime: '08:00',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  },
  keywords: ['urgent', 'bug', 'security'],
  projects: ['project-1', 'project-2'],
};

export const Notifications: React.FC = () => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>(mockNotifications);
  const [showCenter, setShowCenter] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [preferences, setPreferences] = useState(defaultPreferences);
  const [isLoading, setIsLoading] = useState(false);

  const handleMarkAsRead = (notification: Notification) => {
    setNotifications(prev => prev.map(n =>
      n.id === notification.id
        ? { ...n, isRead: true, readAt: new Date() }
        : n
    ));
  };

  const handleMarkAsUnread = (notification: Notification) => {
    setNotifications(prev => prev.map(n =>
      n.id === notification.id
        ? { ...n, isRead: false, readAt: undefined }
        : n
    ));
  };

  const handleMarkAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({
      ...n,
      isRead: true,
      readAt: n.readAt || new Date(),
    })));
  };

  const handleDismiss = (notification: Notification) => {
    setNotifications(prev => prev.filter(n => n.id !== notification.id));
  };

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear all notifications? This action cannot be undone.')) {
      setNotifications([]);
    }
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      // In a real app, this would fetch fresh notifications from the API
      console.log('Refreshing notifications...');
    } catch (error) {
      console.error('Failed to refresh notifications:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSavePreferences = async (newPreferences: typeof preferences) => {
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      setPreferences(newPreferences);
      console.log('Notification preferences saved:', newPreferences);
    } catch (error) {
      console.error('Failed to save preferences:', error);
      throw error;
    }
  };

  const unreadCount = notifications.filter(n => !n.isRead).length;
  const highPriorityCount = notifications.filter(n => n.priority === 'high' && !n.isRead).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center space-x-3">
            <Bell className="h-8 w-8" />
            <span>Notifications</span>
            {unreadCount > 0 && (
              <span className="bg-red-500 text-white text-sm px-3 py-1 rounded-full">
                {unreadCount}
              </span>
            )}
          </h1>
          <p className="text-muted-foreground">
            Stay updated with your team's activities and important events
          </p>
          {highPriorityCount > 0 && (
            <p className="text-red-600 text-sm mt-1">
              {highPriorityCount} high priority notification{highPriorityCount > 1 ? 's' : ''} require your attention
            </p>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          
          {unreadCount > 0 && (
            <Button
              variant="outline"
              onClick={handleMarkAllAsRead}
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Mark All Read
            </Button>
          )}
          
          <Button
            variant="outline"
            onClick={() => setShowSettings(true)}
          >
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
          
          {notifications.length > 0 && (
            <Button
              variant="outline"
              onClick={handleClearAll}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Clear All
            </Button>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-blue-600">{notifications.length}</div>
          <div className="text-sm text-muted-foreground">Total Notifications</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-red-600">{unreadCount}</div>
          <div className="text-sm text-muted-foreground">Unread</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-orange-600">{highPriorityCount}</div>
          <div className="text-sm text-muted-foreground">High Priority</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-green-600">
            {notifications.filter(n => n.type === 'deployment' && !n.isRead).length}
          </div>
          <div className="text-sm text-muted-foreground">Deployment Updates</div>
        </div>
      </div>

      {/* Open Notification Center */}
      <div className="flex justify-center">
        <Button
          onClick={() => setShowCenter(true)}
          size="lg"
          className="px-8 py-4"
        >
          <Bell className="h-5 w-5 mr-2" />
          Open Notification Center
        </Button>
      </div>

      {/* Recent Notifications Preview */}
      {notifications.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Recent Notifications</h2>
          <div className="space-y-3">
            {notifications.slice(0, 3).map((notification) => (
              <div
                key={notification.id}
                className={`p-4 border rounded-lg ${
                  !notification.isRead ? 'bg-blue-50 border-blue-200' : 'bg-white'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      {!notification.isRead && (
                        <div className="w-2 h-2 bg-blue-500 rounded-full" />
                      )}
                      <h3 className="font-medium">{notification.title}</h3>
                      <span className="text-xs text-gray-500 capitalize">
                        {notification.priority} • {notification.type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{notification.message}</p>
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      <span>{new Date(notification.createdAt).toLocaleString()}</span>
                      {notification.projectName && (
                        <span>Project: {notification.projectName}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {!notification.isRead && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleMarkAsRead(notification)}
                      >
                        Mark Read
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDismiss(notification)}
                    >
                      Dismiss
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {notifications.length > 3 && (
            <div className="text-center">
              <Button
                variant="outline"
                onClick={() => setShowCenter(true)}
              >
                View All {notifications.length} Notifications
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {notifications.length === 0 && (
        <div className="text-center py-12">
          <Bell className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No notifications</h3>
          <p className="text-gray-500 mb-4">
            You're all caught up! Notifications about team activities will appear here.
          </p>
          <Button onClick={() => setShowSettings(true)}>
            <Settings className="h-4 w-4 mr-2" />
            Configure Notifications
          </Button>
        </div>
      )}

      {/* Modals */}
      <NotificationCenter
        isOpen={showCenter}
        onClose={() => setShowCenter(false)}
        notifications={notifications}
        onMarkAsRead={handleMarkAsRead}
        onMarkAsUnread={handleMarkAsUnread}
        onMarkAllAsRead={handleMarkAllAsRead}
        onDismiss={handleDismiss}
        onClearAll={handleClearAll}
        onRefresh={handleRefresh}
        onOpenSettings={() => {
          setShowCenter(false);
          setShowSettings(true);
        }}
        isLoading={isLoading}
      />

      <NotificationSettings
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        preferences={preferences}
        onSave={handleSavePreferences}
        availableProjects={mockProjects}
      />
    </div>
  );
};