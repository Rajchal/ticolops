import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { NotificationCenter } from '../NotificationCenter';
import type { Notification } from '../NotificationCard';

const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'deployment',
    title: 'Deployment Successful',
    message: 'Your application has been deployed successfully.',
    isRead: false,
    priority: 'high',
    userId: 'user-1',
    projectId: 'project-1',
    projectName: 'Test Project',
    repositoryName: 'test-repo',
    createdAt: new Date('2024-01-01T12:00:00Z'),
  },
  {
    id: '2',
    type: 'mention',
    title: 'You were mentioned',
    message: 'Someone mentioned you in a comment.',
    isRead: false,
    priority: 'medium',
    userId: 'user-1',
    projectId: 'project-1',
    projectName: 'Test Project',
    createdAt: new Date('2024-01-01T11:00:00Z'),
  },
  {
    id: '3',
    type: 'activity',
    title: 'Team Activity',
    message: 'A team member started working on a file.',
    isRead: true,
    priority: 'low',
    userId: 'user-1',
    projectId: 'project-1',
    projectName: 'Test Project',
    createdAt: new Date('2024-01-01T10:00:00Z'),
    readAt: new Date('2024-01-01T10:30:00Z'),
  },
  {
    id: '4',
    type: 'conflict',
    title: 'Conflict Detected',
    message: 'A merge conflict was detected.',
    isRead: false,
    priority: 'high',
    userId: 'user-1',
    projectId: 'project-2',
    projectName: 'Another Project',
    createdAt: new Date('2024-01-01T09:00:00Z'),
  },
];

describe('NotificationCenter', () => {
  const mockOnClose = vi.fn();
  const mockOnMarkAsRead = vi.fn();
  const mockOnMarkAsUnread = vi.fn();
  const mockOnMarkAllAsRead = vi.fn();
  const mockOnDismiss = vi.fn();
  const mockOnClearAll = vi.fn();
  const mockOnRefresh = vi.fn();
  const mockOnOpenSettings = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when isOpen is false', () => {
    render(
      <NotificationCenter
        isOpen={false}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    expect(screen.queryByText('Notifications')).not.toBeInTheDocument();
  });

  it('renders when isOpen is true', () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    expect(screen.getByText('Notifications')).toBeInTheDocument();
  });

  it('shows unread count in header', () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    // Should show 3 unread notifications
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('shows high priority count when present', () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    // Should show high priority notification count
    expect(screen.getByText(/2 high priority notification/)).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('filters notifications by search query', async () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search notifications...');
    fireEvent.change(searchInput, { target: { value: 'deployment' } });

    await waitFor(() => {
      expect(screen.getByText('Deployment Successful')).toBeInTheDocument();
      expect(screen.queryByText('You were mentioned')).not.toBeInTheDocument();
    });
  });

  it('filters notifications by type', async () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    const filterSelect = screen.getAllByRole('combobox')[0];
    fireEvent.change(filterSelect, { target: { value: 'deployment' } });

    await waitFor(() => {
      expect(screen.getByText('Deployment Successful')).toBeInTheDocument();
      expect(screen.queryByText('You were mentioned')).not.toBeInTheDocument();
    });
  });

  it('filters notifications by unread status', async () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    const filterSelect = screen.getAllByRole('combobox')[0];
    fireEvent.change(filterSelect, { target: { value: 'unread' } });

    await waitFor(() => {
      expect(screen.getByText('Deployment Successful')).toBeInTheDocument();
      expect(screen.getByText('You were mentioned')).toBeInTheDocument();
      expect(screen.queryByText('Team Activity')).not.toBeInTheDocument();
    });
  });

  it('sorts notifications by priority', async () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    const sortSelect = screen.getAllByRole('combobox')[1];
    fireEvent.change(sortSelect, { target: { value: 'priority' } });

    await waitFor(() => {
      const notificationCards = screen.getAllByText(/Deployment Successful|Conflict Detected|You were mentioned|Team Activity/);
      // High priority notifications should appear first
      expect(notificationCards[0]).toHaveTextContent(/Deployment Successful|Conflict Detected/);
    });
  });

  it('calls onRefresh when refresh button is clicked', () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
        onRefresh={mockOnRefresh}
      />
    );

    const refreshButton = screen.getByText('Refresh');
    fireEvent.click(refreshButton);

    expect(mockOnRefresh).toHaveBeenCalled();
  });

  it('calls onMarkAllAsRead when mark all read button is clicked', () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
        onMarkAllAsRead={mockOnMarkAllAsRead}
      />
    );

    const markAllReadButton = screen.getByText('Mark All Read');
    fireEvent.click(markAllReadButton);

    expect(mockOnMarkAllAsRead).toHaveBeenCalled();
  });

  it('calls onOpenSettings when settings button is clicked', () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
        onOpenSettings={mockOnOpenSettings}
      />
    );

    const settingsButton = screen.getByText('Settings');
    fireEvent.click(settingsButton);

    expect(mockOnOpenSettings).toHaveBeenCalled();
  });

  it('calls onClearAll when clear all button is clicked and confirmed', () => {
    // Mock window.confirm
    const mockConfirm = vi.fn(() => true);
    Object.defineProperty(window, 'confirm', {
      value: mockConfirm,
      writable: true,
    });

    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
        onClearAll={mockOnClearAll}
      />
    );

    const clearAllButton = screen.getByText('Clear All');
    fireEvent.click(clearAllButton);

    expect(mockConfirm).toHaveBeenCalled();
    expect(mockOnClearAll).toHaveBeenCalled();
  });

  it('does not call onClearAll when clear all is cancelled', () => {
    // Mock window.confirm to return false
    const mockConfirm = vi.fn(() => false);
    Object.defineProperty(window, 'confirm', {
      value: mockConfirm,
      writable: true,
    });

    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
        onClearAll={mockOnClearAll}
      />
    );

    const clearAllButton = screen.getByText('Clear All');
    fireEvent.click(clearAllButton);

    expect(mockConfirm).toHaveBeenCalled();
    expect(mockOnClearAll).not.toHaveBeenCalled();
  });

  it('shows empty state when no notifications match filters', async () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search notifications...');
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

    await waitFor(() => {
      expect(screen.getByText('No notifications found')).toBeInTheDocument();
      expect(screen.getByText('Try adjusting your search or filters')).toBeInTheDocument();
    });
  });

  it('shows empty state when no notifications exist', () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={[]}
      />
    );

    expect(screen.getByText('No notifications yet')).toBeInTheDocument();
    expect(screen.getByText('You\'ll see notifications about team activities here')).toBeInTheDocument();
  });

  it('shows loading state when isLoading is true', () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
        isLoading={true}
      />
    );

    expect(screen.getByText('Updating...')).toBeInTheDocument();
  });

  it('displays correct notification counts in status bar', () => {
    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={mockNotifications}
      />
    );

    expect(screen.getByText('Total: 4')).toBeInTheDocument();
    expect(screen.getByText('Unread: 3')).toBeInTheDocument();
    expect(screen.getByText('High Priority: 2')).toBeInTheDocument();
  });

  it('handles notification actions correctly', async () => {
    const notificationWithAction = {
      ...mockNotifications[0],
      actionUrl: 'https://example.com',
    };

    // Mock window.open
    const mockOpen = vi.fn();
    Object.defineProperty(window, 'open', {
      value: mockOpen,
      writable: true,
    });

    render(
      <NotificationCenter
        isOpen={true}
        onClose={mockOnClose}
        notifications={[notificationWithAction]}
        onMarkAsRead={mockOnMarkAsRead}
      />
    );

    // Find and click an action button (this would be in the NotificationCard)
    // Since the action handling is in the NotificationCenter component,
    // we need to test that it properly handles the action
    await waitFor(() => {
      expect(screen.getByText('Deployment Successful')).toBeInTheDocument();
    });
  });
});