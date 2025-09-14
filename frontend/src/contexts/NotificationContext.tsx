import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { websocketService } from '../services/websocketService';
import { useAuth } from './AuthContext';
import type { Notification } from '../components/notifications/NotificationCard';

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, 'id' | 'createdAt'>) => void;
  markAsRead: (notificationId: string) => void;
  markAsUnread: (notificationId: string) => void;
  markAllAsRead: () => void;
  dismissNotification: (notificationId: string) => void;
  clearAllNotifications: () => void;
  refreshNotifications: () => Promise<void>;
  isLoading: boolean;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: ReactNode;
}

// Mock initial notifications
const mockInitialNotifications: Notification[] = [
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
    createdAt: new Date(Date.now() - 5 * 60 * 1000),
  },
  {
    id: '2',
    type: 'mention',
    title: 'You were mentioned',
    message: 'Sarah Chen mentioned you in a comment about the authentication flow.',
    isRead: false,
    priority: 'high',
    userId: 'user-1',
    projectId: 'project-1',
    projectName: 'E-commerce Platform',
    actionUrl: '/projects/project-1#comment-123',
    actionText: 'View Comment',
    createdAt: new Date(Date.now() - 15 * 60 * 1000),
  },
  {
    id: '3',
    type: 'conflict',
    title: 'Merge Conflict Detected',
    message: 'A merge conflict was detected in the user authentication module.',
    isRead: false,
    priority: 'high',
    userId: 'user-1',
    projectId: 'project-1',
    projectName: 'E-commerce Platform',
    repositoryId: 'repo-1',
    repositoryName: 'ecommerce-frontend',
    actionUrl: '/projects/project-1/conflicts',
    actionText: 'Resolve Conflict',
    createdAt: new Date(Date.now() - 30 * 60 * 1000),
  },
];

export const NotificationProvider: React.FC<NotificationProviderProps> = ({ children }) => {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Initialize notifications when user is available
  useEffect(() => {
    if (user) {
      setNotifications(mockInitialNotifications);
    } else {
      setNotifications([]);
    }
  }, [user]);

  // Set up WebSocket listeners for real-time notifications
  useEffect(() => {
    if (!user) return;

    const handleNotification = (data: any) => {
      const notification: Notification = {
        id: data.id || Date.now().toString(),
        type: data.type || 'system',
        title: data.title,
        message: data.message,
        isRead: false,
        priority: data.priority || 'medium',
        userId: user.id,
        projectId: data.projectId,
        projectName: data.projectName,
        repositoryId: data.repositoryId,
        repositoryName: data.repositoryName,
        actionUrl: data.actionUrl,
        actionText: data.actionText,
        createdAt: new Date(data.createdAt || Date.now()),
        metadata: data.metadata,
      };

      setNotifications(prev => [notification, ...prev]);

      // Show browser notification if supported and permitted
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(notification.title, {
          body: notification.message,
          icon: '/favicon.ico',
          tag: notification.id,
        });
      }
    };

    const handleDeploymentNotification = (data: any) => {
      const notification: Notification = {
        id: `deployment-${data.deploymentId}`,
        type: 'deployment',
        title: data.status === 'success' ? 'Deployment Successful' : 'Deployment Failed',
        message: `${data.repositoryName} deployment ${data.status === 'success' ? 'completed successfully' : 'failed'}`,
        isRead: false,
        priority: data.status === 'failed' ? 'high' : 'medium',
        userId: user.id,
        projectId: data.projectId,
        projectName: data.projectName,
        repositoryId: data.repositoryId,
        repositoryName: data.repositoryName,
        actionUrl: data.status === 'success' ? data.deploymentUrl : `/deployments/${data.deploymentId}/logs`,
        actionText: data.status === 'success' ? 'View Deployment' : 'View Logs',
        createdAt: new Date(),
      };

      setNotifications(prev => [notification, ...prev]);
    };

    const handleActivityNotification = (data: any) => {
      const notification: Notification = {
        id: `activity-${data.activityId}`,
        type: 'activity',
        title: 'Team Activity',
        message: data.message,
        isRead: false,
        priority: 'low',
        userId: user.id,
        projectId: data.projectId,
        projectName: data.projectName,
        createdAt: new Date(),
      };

      setNotifications(prev => [notification, ...prev]);
    };

    const handleConflictNotification = (data: any) => {
      const notification: Notification = {
        id: `conflict-${data.conflictId}`,
        type: 'conflict',
        title: 'Conflict Detected',
        message: data.message,
        isRead: false,
        priority: 'high',
        userId: user.id,
        projectId: data.projectId,
        projectName: data.projectName,
        repositoryId: data.repositoryId,
        repositoryName: data.repositoryName,
        actionUrl: `/projects/${data.projectId}/conflicts`,
        actionText: 'Resolve Conflict',
        createdAt: new Date(),
      };

      setNotifications(prev => [notification, ...prev]);
    };

    // Set up WebSocket event listeners
    const socket = websocketService.getSocket();
    if (socket) {
      socket.on('notification', handleNotification);
      socket.on('deployment:status', handleDeploymentNotification);
      socket.on('activity:notification', handleActivityNotification);
      socket.on('conflict:detected', handleConflictNotification);
    }

    // Cleanup
    return () => {
      if (socket) {
        socket.off('notification', handleNotification);
        socket.off('deployment:status', handleDeploymentNotification);
        socket.off('activity:notification', handleActivityNotification);
        socket.off('conflict:detected', handleConflictNotification);
      }
    };
  }, [user]);

  // Request notification permission on mount
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  const addNotification = (notificationData: Omit<Notification, 'id' | 'createdAt'>) => {
    const notification: Notification = {
      ...notificationData,
      id: Date.now().toString(),
      createdAt: new Date(),
    };

    setNotifications(prev => [notification, ...prev]);
  };

  const markAsRead = (notificationId: string) => {
    setNotifications(prev => prev.map(notification =>
      notification.id === notificationId
        ? { ...notification, isRead: true, readAt: new Date() }
        : notification
    ));
  };

  const markAsUnread = (notificationId: string) => {
    setNotifications(prev => prev.map(notification =>
      notification.id === notificationId
        ? { ...notification, isRead: false, readAt: undefined }
        : notification
    ));
  };

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(notification => ({
      ...notification,
      isRead: true,
      readAt: notification.readAt || new Date(),
    })));
  };

  const dismissNotification = (notificationId: string) => {
    setNotifications(prev => prev.filter(notification => notification.id !== notificationId));
  };

  const clearAllNotifications = () => {
    setNotifications([]);
  };

  const refreshNotifications = async () => {
    setIsLoading(true);
    try {
      // Simulate API call to fetch fresh notifications
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // In a real app, this would fetch from the API
      // const freshNotifications = await fetchNotifications();
      // setNotifications(freshNotifications);
      
      console.log('Notifications refreshed');
    } catch (error) {
      console.error('Failed to refresh notifications:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const unreadCount = notifications.filter(n => !n.isRead).length;

  const value = {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    markAsUnread,
    markAllAsRead,
    dismissNotification,
    clearAllNotifications,
    refreshNotifications,
    isLoading,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};