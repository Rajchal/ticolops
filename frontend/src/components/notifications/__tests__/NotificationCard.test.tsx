import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { NotificationCard, type Notification } from '../NotificationCard';

const mockNotification: Notification = {
  id: '1',
  type: 'deployment',
  title: 'Deployment Successful',
  message: 'Your application has been deployed successfully.',
  isRead: false,
  priority: 'medium',
  userId: 'user-1',
  projectId: 'project-1',
  projectName: 'Test Project',
  repositoryId: 'repo-1',
  repositoryName: 'test-repo',
  actionUrl: 'https://example.com',
  actionText: 'View Deployment',
  createdAt: new Date('2024-01-01T12:00:00Z'),
};

describe('NotificationCard', () => {
  const mockOnMarkAsRead = vi.fn();
  const mockOnMarkAsUnread = vi.fn();
  const mockOnDismiss = vi.fn();
  const mockOnAction = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders notification content correctly', () => {
    render(
      <NotificationCard
        notification={mockNotification}
        onMarkAsRead={mockOnMarkAsRead}
        onMarkAsUnread={mockOnMarkAsUnread}
        onDismiss={mockOnDismiss}
        onAction={mockOnAction}
      />
    );

    expect(screen.getByText('Deployment Successful')).toBeInTheDocument();
    expect(screen.getByText('Your application has been deployed successfully.')).toBeInTheDocument();
    expect(screen.getByText('Test Project')).toBeInTheDocument();
    expect(screen.getByText('test-repo')).toBeInTheDocument();
  });

  it('shows unread indicator for unread notifications', () => {
    render(
      <NotificationCard
        notification={mockNotification}
        onMarkAsRead={mockOnMarkAsRead}
      />
    );

    // Should show unread dot
    const unreadDot = document.querySelector('.bg-yellow-500');
    expect(unreadDot).toBeInTheDocument();
  });

  it('does not show unread indicator for read notifications', () => {
    const readNotification = { ...mockNotification, isRead: true, readAt: new Date() };
    
    render(
      <NotificationCard
        notification={readNotification}
        onMarkAsRead={mockOnMarkAsRead}
      />
    );

    // Should not show unread dot
    const unreadDot = document.querySelector('.bg-yellow-500');
    expect(unreadDot).not.toBeInTheDocument();
  });

  it('calls onMarkAsRead when mark as read button is clicked', () => {
    render(
      <NotificationCard
        notification={mockNotification}
        onMarkAsRead={mockOnMarkAsRead}
        showActions={true}
      />
    );

    const markAsReadButton = screen.getByTitle('Mark as read');
    fireEvent.click(markAsReadButton);

    expect(mockOnMarkAsRead).toHaveBeenCalledWith(mockNotification);
  });

  it('calls onMarkAsUnread when mark as unread button is clicked', () => {
    const readNotification = { ...mockNotification, isRead: true, readAt: new Date() };
    
    render(
      <NotificationCard
        notification={readNotification}
        onMarkAsUnread={mockOnMarkAsUnread}
        showActions={true}
      />
    );

    const markAsUnreadButton = screen.getByTitle('Mark as unread');
    fireEvent.click(markAsUnreadButton);

    expect(mockOnMarkAsUnread).toHaveBeenCalledWith(readNotification);
  });

  it('calls onDismiss when dismiss button is clicked', () => {
    render(
      <NotificationCard
        notification={mockNotification}
        onDismiss={mockOnDismiss}
        showActions={true}
      />
    );

    const dismissButton = screen.getByTitle('Dismiss');
    fireEvent.click(dismissButton);

    expect(mockOnDismiss).toHaveBeenCalledWith(mockNotification);
  });

  it('calls onAction when action button is clicked', () => {
    render(
      <NotificationCard
        notification={mockNotification}
        onAction={mockOnAction}
        showActions={true}
      />
    );

    const actionButton = screen.getByText('View Deployment');
    fireEvent.click(actionButton);

    expect(mockOnAction).toHaveBeenCalledWith(mockNotification);
  });

  it('renders in compact mode correctly', () => {
    render(
      <NotificationCard
        notification={mockNotification}
        compact={true}
      />
    );

    // In compact mode, should still show title and message but in a more condensed format
    expect(screen.getByText('Deployment Successful')).toBeInTheDocument();
    expect(screen.getByText('Your application has been deployed successfully.')).toBeInTheDocument();
  });

  it('displays correct priority styling for high priority notifications', () => {
    const highPriorityNotification = { ...mockNotification, priority: 'high' as const };
    
    render(
      <NotificationCard
        notification={highPriorityNotification}
      />
    );

    // Should have red border for high priority
    const card = document.querySelector('.border-l-red-500');
    expect(card).toBeInTheDocument();
  });

  it('displays correct priority styling for low priority notifications', () => {
    const lowPriorityNotification = { ...mockNotification, priority: 'low' as const };
    
    render(
      <NotificationCard
        notification={lowPriorityNotification}
      />
    );

    // Should have blue border for low priority
    const card = document.querySelector('.border-l-blue-500');
    expect(card).toBeInTheDocument();
  });

  it('shows correct icon for different notification types', () => {
    const activityNotification = { ...mockNotification, type: 'activity' as const };
    
    render(
      <NotificationCard
        notification={activityNotification}
      />
    );

    // Should show Users icon for activity type
    const icon = document.querySelector('.text-blue-500');
    expect(icon).toBeInTheDocument();
  });

  it('does not show actions when showActions is false', () => {
    render(
      <NotificationCard
        notification={mockNotification}
        showActions={false}
      />
    );

    expect(screen.queryByTitle('Mark as read')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Dismiss')).not.toBeInTheDocument();
  });

  it('formats timestamp correctly', () => {
    render(
      <NotificationCard
        notification={mockNotification}
      />
    );

    // Should show relative time
    expect(screen.getByText(/ago/)).toBeInTheDocument();
  });
});