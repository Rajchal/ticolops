import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LogOut, User, Settings } from 'lucide-react';
import { Button } from '../ui/Button';
import { NotificationBell } from '../notifications/NotificationBell';
import { NotificationCenter } from '../notifications/NotificationCenter';
import { useAuth } from '../../contexts/AuthContext';
import { useNotifications } from '../../contexts/NotificationContext';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const {
    notifications,
    markAsRead,
    markAsUnread,
    markAllAsRead,
    dismissNotification,
    clearAllNotifications,
    refreshNotifications,
    isLoading,
  } = useNotifications();
  const [showNotificationCenter, setShowNotificationCenter] = useState(false);

  return (
    <header className="border-b bg-card">
      <div className="flex h-16 items-center px-6">
        <Link to="/" className="flex items-center space-x-2">
          <div className="h-8 w-8 bg-primary rounded-md flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">T</span>
          </div>
          <span className="font-bold text-xl">Ticolops</span>
        </Link>
        
        <div className="ml-auto flex items-center space-x-4">
          {user && (
            <>
              <NotificationBell
                notifications={notifications}
                onMarkAsRead={markAsRead}
                onMarkAsUnread={markAsUnread}
                onDismiss={dismissNotification}
                onOpenCenter={() => setShowNotificationCenter(true)}
              />
              
              <div className="flex items-center space-x-2">
                <User className="h-4 w-4" />
                <span className="text-sm font-medium">{user.name}</span>
                <span className="text-xs text-muted-foreground capitalize">
                  ({user.role})
                </span>
              </div>
              
              <Link to="/profile">
                <Button variant="outline" size="sm">
                  <Settings className="h-4 w-4 mr-2" />
                  Profile
                </Button>
              </Link>
              
              <Button variant="outline" size="sm" onClick={logout}>
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </>
          )}
        </div>
        
        {/* Notification Center Modal */}
        <NotificationCenter
          isOpen={showNotificationCenter}
          onClose={() => setShowNotificationCenter(false)}
          notifications={notifications}
          onMarkAsRead={markAsRead}
          onMarkAsUnread={markAsUnread}
          onMarkAllAsRead={markAllAsRead}
          onDismiss={dismissNotification}
          onClearAll={clearAllNotifications}
          onRefresh={refreshNotifications}
          onOpenSettings={() => {
            setShowNotificationCenter(false);
            navigate('/notifications');
          }}
          isLoading={isLoading}
        />
      </div>
    </header>
  );
};