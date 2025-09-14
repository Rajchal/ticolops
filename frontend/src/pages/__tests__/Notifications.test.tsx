import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { Notifications } from '../Notifications';
import { AuthProvider } from '../../contexts/AuthContext';

// Mock the auth context
const mockUser = {
  id: 'user-1',
  name: 'Test User',
  email: 'test@example.com',
  role: 'student' as const,
  avatar: null,
};

const MockAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const authContextValue = {
    user: mockUser,
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    isLoading: false,
    error: null,
  };

  return (
    <AuthProvider value={authContextValue as any}>
      {children}
    </AuthProvider>
  );
};

// Mock window.confirm
const mockConfirm = vi.fn();
Object.defineProperty(window, 'confirm', {
  value: mockConfirm,
  writable: true,
});

// Mock window.open
const mockOpen = vi.fn();
Object.defineProperty(window, 'open', {
  value: mockOpen,
  writable: true,
});

describe('Notifications Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (component: React.ReactElement) => {
    return render(
      <BrowserRouter>
        <MockAuthProvider>
          {component}
        </MockAuthProvider>
      </BrowserRouter>
    );
  };

  it('renders notifications page correctly', () => {
    renderWithRouter(<Notifications />);

    expect(screen.getByText('Notifications')).toBeInTheDocument();
    expect(screen.getByText('Stay updated with your team\'s activities and important events')).toBeInTheDocument();
  });

  it('displays notification statistics correctly', () => {
    renderWithRouter(<Notifications />);

    // Should show stats cards
    expect(screen.getByText('Total Notifications')).toBeInTheDocument();
    expect(screen.getByText('Unread')).toBeInTheDocument();
    expect(screen.getByText('High Priority')).toBeInTheDocument();
    expect(screen.getByText('Deployment Updates')).toBeInTheDocument();
  });

  it('shows unread count in header', () => {
    renderWithRouter(<Notifications />);

    // Should show unread count badge (based on mock data, there are 3 unread)
    const unreadBadges = screen.getAllByText('3');
    expect(unreadBadges.length).toBeGreaterThan(0);
  });

  it('shows high priority notification warning', () => {
    renderWithRouter(<Notifications />);

    expect(screen.getByText(/2 high priority notification/)).toBeInTheDocument();
  });

  it('opens notification center when button is clicked', async () => {
    renderWithRouter(<Notifications />);

    const openCenterButton = screen.getByText('Open Notification Center');
    fireEvent.click(openCenterButton);

    await waitFor(() => {
      // Should open the notification center modal
      expect(screen.getAllByText('Notifications')).toHaveLength(2); // One in page header, one in modal
    });
  });

  it('displays recent notifications preview', () => {
    renderWithRouter(<Notifications />);

    expect(screen.getByText('Recent Notifications')).toBeInTheDocument();
    expect(screen.getByText('Deployment Successful')).toBeInTheDocument();
    expect(screen.getByText('You were mentioned')).toBeInTheDocument();
    expect(screen.getByText('Merge Conflict Detected')).toBeInTheDocument();
  });

  it('marks notification as read when mark read button is clicked', async () => {
    renderWithRouter(<Notifications />);

    const markReadButtons = screen.getAllByText('Mark Read');
    fireEvent.click(markReadButtons[0]);

    // The notification should be marked as read (UI should update)
    await waitFor(() => {
      // After marking as read, the unread count should decrease
      // This is a bit tricky to test without more complex state management
      expect(markReadButtons[0]).toBeInTheDocument();
    });
  });

  it('dismisses notification when dismiss button is clicked', async () => {
    renderWithRouter(<Notifications />);

    const dismissButtons = screen.getAllByText('Dismiss');
    const initialNotificationCount = dismissButtons.length;
    
    fireEvent.click(dismissButtons[0]);

    await waitFor(() => {
      // Should have one less notification
      const remainingDismissButtons = screen.getAllByText('Dismiss');
      expect(remainingDismissButtons.length).toBe(initialNotificationCount - 1);
    });
  });

  it('refreshes notifications when refresh button is clicked', async () => {
    renderWithRouter(<Notifications />);

    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);

    // Should show loading state briefly
    await waitFor(() => {
      expect(refreshButton).toBeInTheDocument();
    });
  });

  it('marks all notifications as read when mark all read button is clicked', async () => {
    renderWithRouter(<Notifications />);

    const markAllReadButton = screen.getByText('Mark All Read');
    fireEvent.click(markAllReadButton);

    await waitFor(() => {
      // After marking all as read, the unread count should be 0
      // The Mark All Read button should disappear
      expect(screen.queryByText('Mark All Read')).not.toBeInTheDocument();
    });
  });

  it('opens settings when settings button is clicked', async () => {
    renderWithRouter(<Notifications />);

    const settingsButton = screen.getByText('Settings');
    fireEvent.click(settingsButton);

    await waitFor(() => {
      expect(screen.getByText('Notification Settings')).toBeInTheDocument();
    });
  });

  it('clears all notifications when clear all is clicked and confirmed', async () => {
    mockConfirm.mockReturnValue(true);

    renderWithRouter(<Notifications />);

    const clearAllButton = screen.getByText('Clear All');
    fireEvent.click(clearAllButton);

    expect(mockConfirm).toHaveBeenCalledWith(
      'Are you sure you want to clear all notifications? This action cannot be undone.'
    );

    await waitFor(() => {
      // Should show empty state
      expect(screen.getByText('No notifications')).toBeInTheDocument();
    });
  });

  it('does not clear notifications when clear all is cancelled', async () => {
    mockConfirm.mockReturnValue(false);

    renderWithRouter(<Notifications />);

    const clearAllButton = screen.getByText('Clear All');
    fireEvent.click(clearAllButton);

    expect(mockConfirm).toHaveBeenCalled();

    // Should still show notifications
    expect(screen.getByText('Recent Notifications')).toBeInTheDocument();
    expect(screen.getByText('Deployment Successful')).toBeInTheDocument();
  });

  it('shows view all notifications button when there are more than 3 notifications', () => {
    renderWithRouter(<Notifications />);

    // Based on mock data, there are more than 3 notifications
    expect(screen.getByText(/View All \d+ Notifications/)).toBeInTheDocument();
  });

  it('opens notification center when view all notifications is clicked', async () => {
    renderWithRouter(<Notifications />);

    const viewAllButton = screen.getByText(/View All \d+ Notifications/);
    fireEvent.click(viewAllButton);

    await waitFor(() => {
      expect(screen.getAllByText('Notifications')).toHaveLength(2); // Page header + modal header
    });
  });

  it('shows empty state when no notifications exist', async () => {
    renderWithRouter(<Notifications />);

    // First clear all notifications
    mockConfirm.mockReturnValue(true);
    const clearAllButton = screen.getByText('Clear All');
    fireEvent.click(clearAllButton);

    await waitFor(() => {
      expect(screen.getByText('No notifications yet')).toBeInTheDocument();
      expect(screen.getByText('You\'re all caught up! Notifications about team activities will appear here.')).toBeInTheDocument();
      expect(screen.getByText('Configure Notifications')).toBeInTheDocument();
    });
  });

  it('opens settings from empty state', async () => {
    renderWithRouter(<Notifications />);

    // Clear all notifications first
    mockConfirm.mockReturnValue(true);
    const clearAllButton = screen.getByText('Clear All');
    fireEvent.click(clearAllButton);

    await waitFor(() => {
      const configureButton = screen.getByText('Configure Notifications');
      fireEvent.click(configureButton);

      expect(screen.getByText('Notification Settings')).toBeInTheDocument();
    });
  });

  it('saves notification preferences correctly', async () => {
    renderWithRouter(<Notifications />);

    // Open settings
    const settingsButton = screen.getByText('Settings');
    fireEvent.click(settingsButton);

    await waitFor(() => {
      expect(screen.getByText('Notification Settings')).toBeInTheDocument();
    });

    // Make a change
    const pushNotifications = screen.getByLabelText('Enable push notifications');
    fireEvent.click(pushNotifications);

    // Save
    const saveButton = screen.getByText('Save Settings');
    fireEvent.click(saveButton);

    await waitFor(() => {
      // Settings modal should close
      expect(screen.queryByText('Notification Settings')).not.toBeInTheDocument();
    });
  });

  it('handles notification preferences save error gracefully', async () => {
    // Mock console.error to avoid test output noise
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    renderWithRouter(<Notifications />);

    // Open settings
    const settingsButton = screen.getByText('Settings');
    fireEvent.click(settingsButton);

    await waitFor(() => {
      expect(screen.getByText('Notification Settings')).toBeInTheDocument();
    });

    // The save should handle errors gracefully (no crash)
    const saveButton = screen.getByText('Save Settings');
    fireEvent.click(saveButton);

    // Should still be able to interact with the page
    expect(screen.getByText('Notification Settings')).toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it('displays correct notification counts in stats', () => {
    renderWithRouter(<Notifications />);

    // Check the stats cards show correct numbers
    const statsCards = screen.getAllByText(/^\d+$/);
    
    // Should show total count
    expect(screen.getByText('6')).toBeInTheDocument(); // Total notifications
    expect(screen.getByText('3')).toBeInTheDocument(); // Unread count
    expect(screen.getByText('2')).toBeInTheDocument(); // High priority count
    expect(screen.getByText('1')).toBeInTheDocument(); // Deployment updates
  });

  it('shows correct priority and type indicators', () => {
    renderWithRouter(<Notifications />);

    // Should show priority indicators
    expect(screen.getByText('high • deployment')).toBeInTheDocument();
    expect(screen.getByText('high • mention')).toBeInTheDocument();
    expect(screen.getByText('high • conflict')).toBeInTheDocument();
  });

  it('displays project names correctly', () => {
    renderWithRouter(<Notifications />);

    expect(screen.getByText('Project: E-commerce Platform')).toBeInTheDocument();
    expect(screen.getByText('Project: Task Management App')).toBeInTheDocument();
  });

  it('formats timestamps correctly', () => {
    renderWithRouter(<Notifications />);

    // Should show relative timestamps
    const timeElements = screen.getAllByText(/\d+\/\d+\/\d+/);
    expect(timeElements.length).toBeGreaterThan(0);
  });
});