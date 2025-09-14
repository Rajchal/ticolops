import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { NotificationBell } from '../NotificationBell';
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
];

describe('NotificationBell', () => {
  const mockOnMarkAsRead = vi.fn();
  const mockOnMarkAsUnread = vi.fn();
  const mockOnDismiss = vi.fn();
  const mockOnOpenCenter = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders notification bell button', () => {
    render(
      <NotificationBell
        notifications={mockNotifications}
        onMarkAsRead={mockOnMarkAsRead}
        onOpenCenter={mockOnOpenCenter}
      />
    );

    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('shows unread count badge when there are unread notifications', () => {
    render(
      <NotificationBell
        notifications={mockNotifications}
        onMarkAsRead={mockOnMarkAsRead}
        showBadge={true}
      />
    );

    // Should show badge with count of 2 (2 unread notifications)
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('does not show badge when showBadge is false', () => {
    render(
      <NotificationBell
        notifications={mockNotifications}
        onMarkAsRead={mockOnMarkAsRead}
        showBadge={false}
      />
    );

    expect(screen.queryByText('2')).not.toBeInTheDocument();
  });

  it('shows animated bell icon for high priority notifications', () => {
    render(
      <NotificationBell
        notifications={mockNotifications}
        onMarkAsRead={mockOnMarkAsRead}
      />
    );

    // Should have animate-pulse class for high priority notifications
    const button = screen.getByRole('button');
    expect(button).toHaveClass('animate-pulse');
  });

  it('opens dropdown when bell is clicked', async () => {
    render(
      <NotificationBell
        notifications={mockNotifications}
        onMarkAsRead={mockOnMarkAsRead}
      />
    );

    const bellButton = screen.getByRole('button');
    fireEvent.click(bellButton);

    await waitFor(() => {
      expect(screen.getByText('Notifications')).toBeInTheDocument();
    });
  });

  it('shows preview notifications in dropdown', async () => {
    render(
      <NotificationBell
        notifications={mockNotifications}
        onMarkAsRead={mockOnMarkAsRead}
        maxPreviewItems={3}
      />
    );

    const bellButton = screen.getByRole('button');
    fireEvent.click(bellButton);

    await waitFor(() => {
      expect(screen.getByText('Deployment Successful')).toBeInTheDocument();
      expect(screen.getByText('You were mentioned')).toBeInTheDocument();
    });
  });

  it('limits preview notifications to maxPreviewItems', async () => {
    render(
      <NotificationBell
        notifications={mockNotifications}
        onMarkAsRead={mockOnMarkAsRead}
        maxPreviewItems={1}
      />
    );

    const bellButton = screen.getByRole('button');
    fireEvent.click(bellButton);

    await waitFor(() => {
      expect(screen.getByText('Deployment Successful')).toBeInTheDocument();
      // Should not show the second notification due to limit
      expect(screen.queryByText('You were mentioned')).not.toBeInTheDocument();
    });
  });

  it('calls onOpenCenter when "View All" is clicked', async () => {
    render(
      <NotificationBell
        notifications={mockNotifications}
        onMarkAsRead={mockOnMarkAsRead}
        onOpenCenter={mockOnOpenCenter}
      />
    );

    const bellButton = screen.getByRole('button');
    fireEvent.click(bellButton);

    await waitFor(() => {
      const viewAllButton = screen.getByText('View All');
      fireEvent.click(viewAllButton);
      expect(mockOnOpenCenter).toHaveBeenCalled();
    });
  });

  it('calls onMarkAsRead when notification is clicked', async () => {
    render(
      <NotificationBell
        notifications={mockNotifications}
        onMarkAsRead={mockOnMarkAsRead}
      />
    );

    const bellButton = screen.getByRole('button');
    fireEvent.click(bellButton);

    await waitFor(() => {
      const notificationCard = screen.getByText('Deployment Successful').closest('div');
      if (notificationCard) {
        fireEvent.click(notificationCard);
        expect(mockOnMarkAsRead).toHaveBeenCalledWith(mockNotifications[0]);
      }
    });
  });

  it('calls onDismiss when dismiss button is clicked', async () => {
    render(
      <NotificationBell
        notifications={mockNotifications}
        onMarkAsRead={mockOnMarkAsRead}
        onDismiss={mockOnDismiss}
      />
    );

    const bellButton = screen.getByRole('button');
    fireEvent.click(bellButton);

    await waitFor(() => {
      // Find and click the dismiss button (X icon)
      const dismissButtons = screen.getAllByRole('button');
      const dismissButton = dismissButtons.find(button => 
        button.querySelector('svg') && button.getAttribute('class')?.includes('h-6 w-6 p-0')
      );
      
      if (dismissButton) {
        fireEvent.click(dismissButton);
        expect(mockOnDismiss).toHaveBeenCalled();
      }
    });
  });

  it('shows empty state when no notifications', async () => {
    render(
      <NotificationBell
        notifications={[]}
        onMarkAsRead={mockOnMarkAsRead}
      />
    );

    const bellButton = screen.getByRole('button');
    fireEvent.click(bellButton);

    await waitFor(() => {
      expect(screen.getByText('No notifications')).toBeInTheDocument();
    });
  });

  it('closes dropdown when clicking outside', async () => {
    render(
      <div>
        <NotificationBell
          notifications={mockNotifications}
          onMarkAsRead={mockOnMarkAsRead}
        />
        <div data-testid="outside">Outside element</div>
      </div>
    );

    const bellButton = screen.getByRole('button');
    fireEvent.click(bellButton);

    await waitFor(() => {
      expect(screen.getByText('Notifications')).toBeInTheDocument();
    });

    // Click outside
    const outsideElement = screen.getByTestId('outside');
    fireEvent.mouseDown(outsideElement);

    await waitFor(() => {
      expect(screen.queryByText('Notifications')).not.toBeInTheDocument();
    });
  });

  it('handles action URL clicks correctly', async () => {
    const notificationWithAction = {
      ...mockNotifications[0],
      actionUrl: 'https://example.com',
      actionText: 'View Deployment',
    };

    // Mock window.open
    const mockOpen = vi.fn();
    Object.defineProperty(window, 'open', {
      value: mockOpen,
      writable: true,
    });

    render(
      <NotificationBell
        notifications={[notificationWithAction]}
        onMarkAsRead={mockOnMarkAsRead}
      />
    );

    const bellButton = screen.getByRole('button');
    fireEvent.click(bellButton);

    await waitFor(() => {
      const actionButton = screen.getByRole('button', { name: /external/i });
      fireEvent.click(actionButton);
      
      expect(mockOpen).toHaveBeenCalledWith('https://example.com', '_blank');
      expect(mockOnMarkAsRead).toHaveBeenCalledWith(notificationWithAction);
    });
  });
});