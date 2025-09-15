import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { NotificationBell } from '../NotificationBell';
import { NotificationCard, type Notification } from '../NotificationCard';

// Simple integration test for notification components
describe('Notification Components Integration', () => {
    const mockNotification: Notification = {
        id: '1',
        type: 'deployment',
        title: 'Test Notification',
        message: 'This is a test notification message.',
        isRead: false,
        priority: 'medium',
        userId: 'user-1',
        createdAt: new Date('2024-01-01T12:00:00Z'),
    };

    it('renders notification card with basic content', () => {
        render(<NotificationCard notification={mockNotification} />);

        expect(screen.getByText('Test Notification')).toBeInTheDocument();
        expect(screen.getByText('This is a test notification message.')).toBeInTheDocument();
    });

    it('renders notification bell with count', () => {
        const mockOnMarkAsRead = vi.fn();

        render(
            <NotificationBell
                notifications={[mockNotification]}
                onMarkAsRead={mockOnMarkAsRead}
                showBadge={true}
            />
        );

        // Should show the bell button
        expect(screen.getByRole('button')).toBeInTheDocument();

        // Should show unread count badge
        expect(screen.getByText('1')).toBeInTheDocument();
    });

    it('handles notification actions', () => {
        const mockOnMarkAsRead = vi.fn();
        const mockOnDismiss = vi.fn();

        render(
            <NotificationCard
                notification={mockNotification}
                onMarkAsRead={mockOnMarkAsRead}
                onDismiss={mockOnDismiss}
                showActions={true}
            />
        );

        // Should render without errors
        expect(screen.getByText('Test Notification')).toBeInTheDocument();
    });

    it('shows correct priority styling', () => {
        const highPriorityNotification = {
            ...mockNotification,
            priority: 'high' as const,
        };

        render(<NotificationCard notification={highPriorityNotification} />);

        // Should render the notification
        expect(screen.getByText('Test Notification')).toBeInTheDocument();
    });

    it('displays different notification types correctly', () => {
        const notifications: Notification[] = [
            { ...mockNotification, id: '1', type: 'deployment', title: 'Deployment' },
            { ...mockNotification, id: '2', type: 'mention', title: 'Mention' },
            { ...mockNotification, id: '3', type: 'conflict', title: 'Conflict' },
            { ...mockNotification, id: '4', type: 'activity', title: 'Activity' },
            { ...mockNotification, id: '5', type: 'system', title: 'System' },
        ];

        notifications.forEach((notification) => {
            const { unmount } = render(<NotificationCard notification={notification} />);
            expect(screen.getByText(notification.title)).toBeInTheDocument();
            unmount();
        });
    });

    it('handles read/unread states correctly', () => {
        const unreadNotification = { ...mockNotification, isRead: false };
        const readNotification = { ...mockNotification, isRead: true, readAt: new Date() };

        // Test unread notification
        const { rerender } = render(<NotificationCard notification={unreadNotification} />);
        expect(screen.getByText('Test Notification')).toBeInTheDocument();

        // Test read notification
        rerender(<NotificationCard notification={readNotification} />);
        expect(screen.getByText('Test Notification')).toBeInTheDocument();
    });

    it('renders notification bell with multiple notifications', () => {
        const notifications = [
            { ...mockNotification, id: '1', isRead: false },
            { ...mockNotification, id: '2', isRead: false },
            { ...mockNotification, id: '3', isRead: true },
        ];

        render(
            <NotificationBell
                notifications={notifications}
                onMarkAsRead={vi.fn()}
                showBadge={true}
            />
        );

        // Should show unread count (2 unread notifications)
        expect(screen.getByText('2')).toBeInTheDocument();
    });

    it('handles empty notification list', () => {
        render(
            <NotificationBell
                notifications={[]}
                onMarkAsRead={vi.fn()}
                showBadge={true}
            />
        );

        // Should still render the bell button
        expect(screen.getByRole('button')).toBeInTheDocument();

        // Should not show badge when no notifications
        expect(screen.queryByText('0')).not.toBeInTheDocument();
    });

    it('renders compact notification card correctly', () => {
        render(
            <NotificationCard
                notification={mockNotification}
                compact={true}
            />
        );

        expect(screen.getByText('Test Notification')).toBeInTheDocument();
        expect(screen.getByText('This is a test notification message.')).toBeInTheDocument();
    });

    it('handles notification with action URL', () => {
        const notificationWithAction = {
            ...mockNotification,
            actionUrl: 'https://example.com',
            actionText: 'View Details',
        };

        render(
            <NotificationCard
                notification={notificationWithAction}
                showActions={true}
            />
        );

        expect(screen.getByText('Test Notification')).toBeInTheDocument();
        expect(screen.getByText('View Details')).toBeInTheDocument();
    });
});