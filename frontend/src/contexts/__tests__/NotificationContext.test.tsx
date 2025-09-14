import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { vi } from 'vitest';
import { NotificationProvider, useNotifications } from '../NotificationContext';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { it } from 'node:test';
import { websocketService } from '../../services/websocketService';
import { beforeEach } from 'node:test';
import { describe } from 'node:test';

// Mock the websocket service
vi.mock('../../services/websocketService', () => ({
  websocketService: {
    getSocket: vi.fn(() => ({
      on: vi.fn(),
      off: vi.fn(),
      emit: vi.fn(),
    })),
  },
}));

// Mock the auth context
vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      name: 'Test User',
      email: 'test@example.com',
      role: 'student',
      avatar: null,
    },
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    isLoading: false,
    error: null,
  }),
}));

// Test component to access the notification context
const TestComponent: React.FC = () => {
  const {
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
  } = useNotifications();

  return (
    <div>
      <div data-testid="notification-count">{notifications.length}</div>
      <div data-testid="unread-count">{unreadCount}</div>
      <div data-testid="is-loading">{isLoading.toString()}</div>
      
      <button
        onClick={() => addNotification({
          type: 'system',
          title: 'Test Notification',
          message: 'This is a test notification',
          isRead: false,
          priority: 'medium',
          userId: 'user-1',
        })}
        data-testid="add-notification"
      >
        Add Notification
      </button>
      
      <button
        onClick={() => notifications.length > 0 && markAsRead(notifications[0].id)}
        data-testid="mark-as-read"
      >
        Mark First as Read
      </button>
      
      <button
        onClick={() => notifications.length > 0 && markAsUnread(notifications[0].id)}
        data-testid="mark-as-unread"
      >
        Mark First as Unread
      </button>
      
      <button
        onClick={markAllAsRead}
        data-testid="mark-all-read"
      >
        Mark All Read
      </button>
      
      <button
        onClick={() => notifications.length > 0 && dismissNotification(notifications[0].id)}
        data-testid="dismiss-notification"
      >
        Dismiss First
      </button>
      
      <button
        onClick={clearAllNotifications}
        data-testid="clear-all"
      >
        Clear All
      </button>
      
      <button
        onClick={refreshNotifications}
        data-testid="refresh"
      >
        Refresh
      </button>
      
      <div data-testid="notifications">
        {notifications.map((notification) => (
          <div key={notification.id} data-testid={`notification-${notification.id}`}>
            <span data-testid={`title-${notification.id}`}>{notification.title}</span>
            <span data-testid={`read-${notification.id}`}>{notification.isRead.toString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Mock Notification API
const mockNotification = vi.fn();
Object.defineProperty(window, 'Notification', {
  value: mockNotification,
  writable: true,
});

Object.defineProperty(Notification, 'permission', {
  value: 'granted',
  writable: true,
});

Object.defineProperty(Notification, 'requestPermission', {
  value: vi.fn(() => Promise.resolve('granted')),
  writable: true,
});

describe('NotificationContext', () => {
  let mockSocket: any;

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockSocket = {
      on: vi.fn(),
      off: vi.fn(),
      emit: vi.fn(),
    };
    
    (websocketService.getSocket as any).mockReturnValue(mockSocket);
    
    // Reset Notification mock
    mockNotification.mockClear();
  });

  it('provides initial state with mock notifications', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    // Should start with mock notifications since user is mocked
    await waitFor(() => {
      expect(screen.getByTestId('notification-count')).toHaveTextContent('3');
      expect(screen.getByTestId('unread-count')).toHaveTextContent('2');
    });
  });

  it('adds notification correctly', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    // Wait for initial state
    await waitFor(() => {
      expect(screen.getByTestId('notification-count')).toHaveTextContent('3');
    });

    const addButton = screen.getByTestId('add-notification');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByTestId('notification-count')).toHaveTextContent('4');
      expect(screen.getByText('Test Notification')).toBeInTheDocument();
    });
  });

  it('marks notification as read correctly', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    // Wait for initial notifications
    await waitFor(() => {
      expect(screen.getByTestId('notification-count')).toHaveTextContent('3');
      expect(screen.getByTestId('unread-count')).toHaveTextContent('2');
    });

    const markAsReadButton = screen.getByTestId('mark-as-read');
    fireEvent.click(markAsReadButton);

    await waitFor(() => {
      expect(screen.getByTestId('unread-count')).toHaveTextContent('1');
    });
  });

  it('marks notification as unread correctly', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    // Wait for initial notifications
    await waitFor(() => {
      expect(screen.getByTestId('notification-count')).toHaveTextContent('3');
      expect(screen.getByTestId('unread-count')).toHaveTextContent('2');
    });

    // First mark as read, then mark as unread
    const markAsReadButton = screen.getByTestId('mark-as-read');
    fireEvent.click(markAsReadButton);

    await waitFor(() => {
      expect(screen.getByTestId('unread-count')).toHaveTextContent('1');
    });

    const markAsUnreadButton = screen.getByTestId('mark-as-unread');
    fireEvent.click(markAsUnreadButton);

    await waitFor(() => {
      expect(screen.getByTestId('unread-count')).toHaveTextContent('2');
    });
  });

  it('marks all notifications as read correctly', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    // Wait for initial notifications
    await waitFor(() => {
      expect(screen.getByTestId('notification-count')).toHaveTextContent('3');
      expect(screen.getByTestId('unread-count')).toHaveTextContent('2');
    });

    const markAllReadButton = screen.getByTestId('mark-all-read');
    fireEvent.click(markAllReadButton);

    await waitFor(() => {
      expect(screen.getByTestId('unread-count')).toHaveTextContent('0');
    });
  });

  it('dismisses notification correctly', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    // Wait for initial notifications
    await waitFor(() => {
      expect(screen.getByTestId('notification-count')).toHaveTextContent('3');
    });

    const dismissButton = screen.getByTestId('dismiss-notification');
    fireEvent.click(dismissButton);

    await waitFor(() => {
      expect(screen.getByTestId('notification-count')).toHaveTextContent('2');
    });
  });

  it('clears all notifications correctly', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    // Wait for initial notifications
    await waitFor(() => {
      expect(screen.getByTestId('notification-count')).toHaveTextContent('3');
    });

    const clearAllButton = screen.getByTestId('clear-all');
    fireEvent.click(clearAllButton);

    await waitFor(() => {
      expect(screen.getByTestId('notification-count')).toHaveTextContent('0');
      expect(screen.getByTestId('unread-count')).toHaveTextContent('0');
    });
  });

  it('handles refresh notifications correctly', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    const refreshButton = screen.getByTestId('refresh');
    
    act(() => {
      fireEvent.click(refreshButton);
    });

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('true');
    });

    // Should finish loading
    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    }, { timeout: 2000 });
  });

  it('sets up WebSocket event listeners when user is present', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    await waitFor(() => {
      expect(mockSocket.on).toHaveBeenCalledWith('notification', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('deployment:status', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('activity:notification', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('conflict:detected', expect.any(Function));
    });
  });

  it('handles WebSocket notification events correctly', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    // Wait for setup
    await waitFor(() => {
      expect(mockSocket.on).toHaveBeenCalled();
    });

    // Get the notification handler
    const notificationHandler = mockSocket.on.mock.calls.find(
      call => call[0] === 'notification'
    )?.[1];

    expect(notificationHandler).toBeDefined();

    // Simulate receiving a notification
    act(() => {
      notificationHandler({
        id: 'ws-notification-1',
        type: 'system',
        title: 'WebSocket Notification',
        message: 'This came from WebSocket',
        priority: 'high',
      });
    });

    await waitFor(() => {
      expect(screen.getByText('WebSocket Notification')).toBeInTheDocument();
    });
  });

  it('creates browser notifications when permission is granted', async () => {
    render(
      <NotificationProvider>
        <TestComponent />
      </NotificationProvider>
    );

    // Wait for setup
    await waitFor(() => {
      expect(mockSocket.on).toHaveBeenCalled();
    });

    // Get the notification handler
    const notificationHandler = mockSocket.on.mock.calls.find(
      call => call[0] === 'notification'
    )?.[1];

    // Simulate receiving a notification
    act(() => {
      notificationHandler({
        id: 'browser-notification-1',
        type: 'system',
        title: 'Browser Notification',
        message: 'This should create a browser notification',
        priority: 'high',
      });
    });

    await waitFor(() => {
      expect(global.Notification).toHaveBeenCalledWith('Browser Notification', {
        body: 'This should create a browser notification',
        icon: '/favicon.ico',
        tag: 'browser-notification-1',
      });
    });
  });

  it('throws error when useNotifications is used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useNotifications must be used within a NotificationProvider');

    consoleSpy.mockRestore();
  });
});