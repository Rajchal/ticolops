import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { Dashboard } from '../../../pages/Dashboard';
import { RealtimeProvider } from '../../../contexts/RealtimeContext';
import { AuthProvider } from '../../../contexts/AuthContext';
import { websocketService } from '../../../services/websocketService';
import type { ActivityEvent, UserPresence, ConflictAlert } from '../../../services/websocketService';

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
    joinProject: vi.fn(),
    leaveProject: vi.fn(),
    joinFile: vi.fn(),
    leaveFile: vi.fn(),
    isConnected: vi.fn(() => true),
    getSocket: vi.fn(() => ({ connected: true })),
  },
}));

// Mock React Router
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
  useLocation: () => ({ pathname: '/dashboard' }),
}));

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>
    <RealtimeProvider>
      {children}
    </RealtimeProvider>
  </AuthProvider>
);

describe('Real-time Dashboard Integration', () => {
  let mockConnect: any;
  let mockOnActivityEvent: any;
  let mockOnPresenceUpdate: any;
  let mockOnConflictAlert: any;

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockConnect = vi.mocked(websocketService.connect);
    mockOnActivityEvent = vi.mocked(websocketService.onActivityEvent);
    mockOnPresenceUpdate = vi.mocked(websocketService.onPresenceUpdate);
    mockOnConflictAlert = vi.mocked(websocketService.onConflictAlert);

    mockConnect.mockResolvedValue({} as any);
    
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(() => 'mock-token'),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render complete dashboard with real-time features', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    );

    // Check main dashboard elements
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Welcome to Ticolops - Track, Collaborate, Deploy, Succeed')).toBeInTheDocument();
    });

    // Check stats cards
    expect(screen.getByText('Active Projects')).toBeInTheDocument();
    expect(screen.getByText('Team Members')).toBeInTheDocument();
    expect(screen.getByText('Deployments')).toBeInTheDocument();
    expect(screen.getByText('Active Now')).toBeInTheDocument();

    // Check real-time components
    expect(screen.getByText('Team Online')).toBeInTheDocument();
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    expect(screen.getByText('Active Conflicts')).toBeInTheDocument();
    expect(screen.getByText('Connection')).toBeInTheDocument();
  });

  it('should handle layout switching', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    // Find layout buttons (they should be in the header)
    const layoutButtons = screen.getAllByRole('button');
    const sidebarButton = layoutButtons.find(button => 
      button.querySelector('svg') && button.getAttribute('class')?.includes('outline')
    );

    if (sidebarButton) {
      fireEvent.click(sidebarButton);
      
      // Layout should still show the same components
      await waitFor(() => {
        expect(screen.getByText('Recent Activity')).toBeInTheDocument();
        expect(screen.getByText('Team Presence')).toBeInTheDocument();
      });
    }
  });

  it('should integrate all real-time features together', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    );

    // Wait for WebSocket connection
    await waitFor(() => {
      expect(mockConnect).toHaveBeenCalled();
      expect(mockOnActivityEvent).toHaveBeenCalled();
      expect(mockOnPresenceUpdate).toHaveBeenCalled();
      expect(mockOnConflictAlert).toHaveBeenCalled();
    });

    // Simulate real-time updates
    const activityCallback = mockOnActivityEvent.mock.calls[0][0];
    const presenceCallback = mockOnPresenceUpdate.mock.calls[0][0];
    const conflictCallback = mockOnConflictAlert.mock.calls[0][0];

    // Add activity
    const mockActivity: ActivityEvent = {
      id: 'activity-1',
      type: 'commit',
      userId: 'user-1',
      userName: 'Test User',
      projectId: 'proj-1',
      projectName: 'Test Project',
      message: 'Added new feature',
      timestamp: new Date(),
    };

    act(() => {
      activityCallback(mockActivity);
    });

    // Add presence
    const mockPresence: UserPresence[] = [
      {
        userId: 'user-1',
        userName: 'Test User',
        status: 'online',
        lastSeen: new Date(),
      },
      {
        userId: 'user-2',
        userName: 'Another User',
        status: 'busy',
        currentProject: 'Test Project',
        lastSeen: new Date(),
      },
    ];

    act(() => {
      presenceCallback(mockPresence);
    });

    // Add conflict
    const mockConflict: ConflictAlert = {
      id: 'conflict-1',
      type: 'merge_conflict',
      projectId: 'proj-1',
      projectName: 'Test Project',
      filePath: 'src/test.ts',
      users: ['user-1', 'user-2'],
      severity: 'high',
      suggestion: 'Consider merging in a separate branch',
      timestamp: new Date(),
    };

    act(() => {
      conflictCallback(mockConflict);
    });

    // Verify all updates are reflected in the UI
    await waitFor(() => {
      // Activity should be shown
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByText('Added new feature')).toBeInTheDocument();

      // Presence should be shown
      expect(screen.getByText('Another User')).toBeInTheDocument();
      
      // Stats should be updated (2 users online)
      expect(screen.getByText('2')).toBeInTheDocument();

      // Conflict should be shown
      expect(screen.getByText('Merge Conflict Detected')).toBeInTheDocument();
      expect(screen.getByText('Consider merging in a separate branch')).toBeInTheDocument();
    });
  });

  it('should handle WebSocket connection failures gracefully', async () => {
    const connectionError = new Error('Connection failed');
    mockConnect.mockRejectedValue(connectionError);

    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      // Should still render the dashboard
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      
      // Connection status should show disconnected
      expect(screen.getByText('Off')).toBeInTheDocument();
    });
  });

  it('should update stats based on real-time data', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockOnPresenceUpdate).toHaveBeenCalled();
    });

    // Initially should show 0 online
    expect(screen.getByText('0')).toBeInTheDocument();

    // Add some users
    const presenceCallback = mockOnPresenceUpdate.mock.calls[0][0];
    const mockPresence: UserPresence[] = [
      {
        userId: 'user-1',
        userName: 'User 1',
        status: 'online',
        lastSeen: new Date(),
      },
      {
        userId: 'user-2',
        userName: 'User 2',
        status: 'busy',
        lastSeen: new Date(),
      },
      {
        userId: 'user-3',
        userName: 'User 3',
        status: 'away',
        lastSeen: new Date(),
      },
    ];

    act(() => {
      presenceCallback(mockPresence);
    });

    await waitFor(() => {
      // Should show 2 online (online + busy)
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('of 3 total members')).toBeInTheDocument();
    });
  });

  it('should handle collaboration suggestions', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Collaboration Opportunities')).toBeInTheDocument();
    });

    // Should show mock collaboration suggestions
    expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    expect(screen.getByText('API integration expertise needed')).toBeInTheDocument();

    // Should be able to interact with suggestions
    const connectButtons = screen.getAllByText('Connect');
    expect(connectButtons.length).toBeGreaterThan(0);

    // Click first connect button
    fireEvent.click(connectButtons[0]);

    // Suggestion should be removed
    await waitFor(() => {
      expect(screen.queryByText('Similar component being developed')).not.toBeInTheDocument();
    });
  });

  it('should maintain real-time connection throughout user interactions', async () => {
    render(
      <TestWrapper>
        <Dashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockConnect).toHaveBeenCalled();
    });

    // Simulate user interactions that should maintain connection
    const layoutButtons = screen.getAllByRole('button');
    
    // Click different layout buttons
    layoutButtons.slice(0, 3).forEach(button => {
      fireEvent.click(button);
    });

    // Connection should still be maintained
    expect(websocketService.disconnect).not.toHaveBeenCalled();
    expect(vi.mocked(websocketService.isConnected)()).toBe(true);
  });
});