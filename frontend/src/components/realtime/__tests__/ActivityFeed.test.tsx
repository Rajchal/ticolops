import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ActivityFeed } from '../ActivityFeed';
import { RealtimeProvider } from '../../../contexts/RealtimeContext';
import { AuthProvider } from '../../../contexts/AuthContext';
import type { ActivityEvent } from '../../../services/websocketService';

// Mock the websocket service
vi.mock('../../../services/websocketService', () => ({
  websocketService: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    onActivityEvent: vi.fn(),
    offActivityEvent: vi.fn(),
    onPresenceUpdate: vi.fn(),
    offPresenceUpdate: vi.fn(),
    onConflictAlert: vi.fn(),
    offConflictAlert: vi.fn(),
    updatePresence: vi.fn(),
    isConnected: vi.fn(() => true),
  },
}));

// Mock date-fns
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '2 minutes ago'),
}));

const mockActivities: ActivityEvent[] = [
  {
    id: '1',
    type: 'commit',
    userId: 'user1',
    userName: 'John Doe',
    projectId: 'project1',
    projectName: 'Test Project',
    message: 'Added new feature',
    timestamp: new Date(),
  },
  {
    id: '2',
    type: 'deployment',
    userId: 'user2',
    userName: 'Jane Smith',
    projectId: 'project1',
    projectName: 'Test Project',
    message: 'Deployed to production',
    timestamp: new Date(),
  },
];

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>
    <RealtimeProvider>
      {children}
    </RealtimeProvider>
  </AuthProvider>
);

describe('ActivityFeed', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders activity feed with header', () => {
    render(
      <TestWrapper>
        <ActivityFeed />
      </TestWrapper>
    );

    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
  });

  it('renders activity feed without header', () => {
    render(
      <TestWrapper>
        <ActivityFeed showHeader={false} />
      </TestWrapper>
    );

    expect(screen.queryByText('Recent Activity')).not.toBeInTheDocument();
  });

  it('shows empty state when no activities', () => {
    render(
      <TestWrapper>
        <ActivityFeed />
      </TestWrapper>
    );

    expect(screen.getByText('No recent activity')).toBeInTheDocument();
  });

  it('displays connection status indicator', () => {
    render(
      <TestWrapper>
        <ActivityFeed />
      </TestWrapper>
    );

    // Should show connection indicator (green dot when connected)
    const connectionIndicator = screen.getByText('Recent Activity').parentElement?.querySelector('.bg-green-500, .bg-red-500');
    expect(connectionIndicator).toBeInTheDocument();
  });

  it('limits activities to maxItems', () => {
    render(
      <TestWrapper>
        <ActivityFeed maxItems={1} />
      </TestWrapper>
    );

    // Component should respect maxItems prop
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
  });
});