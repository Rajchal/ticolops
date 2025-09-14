import React, { useState, useRef, useEffect } from 'react';
import { Bell, BellRing } from 'lucide-react';
import { Button } from '../ui/Button';
import { NotificationCard, type Notification } from './NotificationCard';

interface NotificationBellProps {
  notifications: Notification[];
  onMarkAsRead?: (notification: Notification) => void;
  onMarkAsUnread?: (notification: Notification) => void;
  onDismiss?: (notification: Notification) => void;
  onOpenCenter?: () => void;
  maxPreviewItems?: number;
  showBadge?: boolean;
}

export const NotificationBell: React.FC<NotificationBellProps> = ({
  notifications,
  onMarkAsRead,
  onMarkAsUnread,
  onDismiss,
  onOpenCenter,
  maxPreviewItems = 5,
  showBadge = true,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const unreadNotifications = notifications.filter(n => !n.isRead);
  const unreadCount = unreadNotifications.length;
  const hasHighPriority = unreadNotifications.some(n => n.priority === 'high');

  // Recent notifications for preview (unread first, then most recent)
  const previewNotifications = [
    ...unreadNotifications.slice(0, maxPreviewItems),
    ...notifications
      .filter(n => n.isRead)
      .slice(0, Math.max(0, maxPreviewItems - unreadNotifications.length))
  ].slice(0, maxPreviewItems);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleAction = (notification: Notification) => {
    if (notification.actionUrl) {
      window.open(notification.actionUrl, '_blank');
      // Mark as read when action is taken
      if (!notification.isRead) {
        onMarkAsRead?.(notification);
      }
    }
    setIsOpen(false);
  };

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.isRead) {
      onMarkAsRead?.(notification);
    }
  };

  return (
    <div className="relative">
      <Button
        ref={buttonRef}
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className={`relative ${hasHighPriority ? 'animate-pulse' : ''}`}
      >
        {hasHighPriority ? (
          <BellRing className="h-4 w-4" />
        ) : (
          <Bell className="h-4 w-4" />
        )}
        
        {showBadge && unreadCount > 0 && (
          <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </Button>

      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute right-0 top-full mt-2 w-96 bg-white border rounded-lg shadow-lg z-50 max-h-96 overflow-hidden"
        >
          <div className="p-3 border-b bg-gray-50">
            <div className="flex items-center justify-between">
              <h3 className="font-medium text-gray-900">
                Notifications
                {unreadCount > 0 && (
                  <span className="ml-2 bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                    {unreadCount}
                  </span>
                )}
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onOpenCenter?.();
                  setIsOpen(false);
                }}
                className="text-xs"
              >
                View All
              </Button>
            </div>
          </div>

          <div className="max-h-80 overflow-y-auto">
            {previewNotifications.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No notifications</p>
              </div>
            ) : (
              <div className="p-2 space-y-2">
                {previewNotifications.map((notification) => (
                  <div
                    key={notification.id}
                    onClick={() => handleNotificationClick(notification)}
                    className="cursor-pointer"
                  >
                    <NotificationCard
                      notification={notification}
                      onMarkAsRead={onMarkAsRead}
                      onMarkAsUnread={onMarkAsUnread}
                      onDismiss={(n) => {
                        onDismiss?.(n);
                        // Don't close dropdown when dismissing
                      }}
                      onAction={handleAction}
                      compact={true}
                      showActions={true}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          {notifications.length > maxPreviewItems && (
            <div className="p-3 border-t bg-gray-50">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onOpenCenter?.();
                  setIsOpen(false);
                }}
                className="w-full text-sm"
              >
                View All {notifications.length} Notifications
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};