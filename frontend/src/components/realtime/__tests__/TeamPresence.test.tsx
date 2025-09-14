import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TeamPresence } from '../TeamPresence';
import { RealtimeProvider } from '../../../contexts/RealtimeContext';
import { AuthProvider } from '../../../contexts/AuthContext';

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
  formatDistanceToNow: vi.fn(() => '5 minutes ago'),
}));

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>
    <RealtimeProvider>
      {children}
    </RealtimeProvider>
  </AuthProvider>
);

describe('TeamPresence', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders team presence with header', () => {
    render(
      <TestWrapper>
        <TeamPresence />
      </TestWrapper>
    );

    expect(screen.getByText('Team Presence')).toBeInTheDocument();
  });

  it('renders team presence without header', () => {
    render(
      <TestWrapper>
        <TeamPresence showHeader={false} />
      </TestWrapper>
    );

    expect(screen.queryByText('Team Presence')).not.toBeInTheDocument();
  });

  it('shows empty state when no team members', () => {
    render(
      <TestWrapper>
        <TeamPresence />
      </TestWrapper>
    );

    expect(screen.getByText('No team members online')).toBeInTheDocument();
  });

  it('displays online count in header', () => {
    render(
      <TestWrapper>
        <TeamPresence />
      </TestWrapper>
    );

    expect(screen.getByText('0 online')).toBeInTheDocument();
  });

  it('displays connection status indicator', () => {
    render(
      <TestWrapper>
        <TeamPresence />
      </TestWrapper>
    );

    // Should show connection indicator (green dot when connected)
    const connectionIndicator = screen.getByText('Team Presence').parentElement?.querySelector('.bg-green-500, .bg-red-500');
    expect(connectionIndicator).toBeInTheDocument();
  });
});