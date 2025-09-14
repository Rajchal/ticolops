import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { RealtimeDashboard } from '../RealtimeDashboard';
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

// Mock user for auth context
const mockUser = {
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'student' as const,
};

// Mock data
const mockActivities: ActivityEvent[] = [
  {
    id: 'activity-1',
    type: 'commit',
    userId: 'user-2',
    userName: 'Sarah Chen',
    userAvatar: undefined,
    projectId: 'proj-1',
    projectName: 'Auth System',
    message: 'Added login validation',
    timestamp: new Date(),
    metadata: {},
  },
  {
    id: 'activity-2',
    type: 'deployment',
    userId: 'user-3',
    userName: 'Mike Johnson',
    userAvatar: undefined,
    projectId: 'proj-2',
    projectName: 'E-commerce Platform',
    message: 'Deployed to staging environment',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    metadata: {},
  },
];

const mockUserPresence: UserPresence[] = [
  {
    userId: 'user-2',
    userName: 'Sarah Chen',
    userAvatar: undefined,
    status: 'online',
    currentProject: 'Auth System',
    currentFile: 'src/components/LoginForm.tsx',
    lastSeen: new Date(),
  },
  {
    userId: 'user-3',
    userName: 'Mike Johnson',
    userAvatar: undefined,
    status: 'busy',
    currentProject: 'E-commerce Platform',
    lastSeen: new Date(),
  },
  {
    userId: 'user-4',
    userName: 'Alex Rodriguez',
    userAvatar: undefined,
    status: 'away',
    lastSeen: new Date(Date.now() - 10 * 60 * 1000),
  },
];

const mockConflicts: ConflictAlert[] = [
  {
    id: 'conflict-1',
    type: 'merge_conflict',
    projectId: 'proj-1',
    projectName: 'Auth System',
    filePath: 'src/services/authService.ts',
    users: ['Sarah Chen', 'Mike Johnson'],
    severity: 'high',
    suggestion: 'Consider merging changes in a shared branch first',
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

describe('RealtimeDashboard Integration Tests', () => {
  let mockConnect: any;
  let mockOnActivityEvent: any;
  let mockOnPresenceUpdate: any;
  let mockOnConflictAlert: any;

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();
    
    // Setup websocket service mocks
    mockConnect = vi.mocked(websocketService.connect);
    mockOnActivityEvent = vi.mocked(websocketService.onActivityEvent);
    mockOnPresenceUpdate = vi.mocked(websocketService.onPresenceUpdate);
    mockOnConflictAlert = vi.mocked(websocketService.onConflictAlert);

    // Mock successful connection
    mockConnect.mockResolvedValue({} as any);
    
    // Mock localStorage for auth token
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

  it('should render dashboard with all components', async () => {
    render(
      <TestWrapper>
        <RealtimeDashboard />
      </TestWrapper>
    );

    // Wait for components to load
    await waitFor(() => {
      expect(screen.getByText('Team Online')).toBeInTheDocument();
      expect(screen.getByText('Recent Activity')).toBeInTheDocument();
      expect(screen.getByText('Active Conflicts')).toBeInTheDocument();
      expect(screen.getByText('Connection')).toBeInTheDocument();
    });

    // Check for main sections
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    expect(screen.getByText('Team Presence')).toBeInTheDocument();
    expect(screen.getByText('Collaboration Opportunities')).toBeInTheDocument();
  });

  it('should handle real-time activity updates', async () => {
    render(
      <TestWrapper>
        <RealtimeDashboard />
      </TestWrapper>
    );

    // Wait for initial render
    await waitFor(() => {
      expect(mockOnActivityEvent).toHaveBeenCalled();
    });

    // Get the activity event callback
    const activityCallback = mockOnActivityEvent.mock.calls[0][0];

    // Simulate receiving a new activity
    activityCallback(mockActivities[0]);

    await waitFor(() => {
      expect(screen.getByText('Sarah Chen')).toBeInTheDocument();
      expect(screen.getByText('Added login validation')).toBeInTheDocument();
      expect(screen.getByText('Auth System')).toBeInTheDocument();
    });
  });

  it('should handle real-time presence updates', async () => {
    render(
      <TestWrapper>
        <RealtimeDashboard />
      </TestWrapper>
    );

    // Wait for initial render
    await waitFor(() => {
      expect(mockOnPresenceUpdate).toHaveBeenCalled();
    });

    // Get the presence update callback
    const presenceCallback = mockOnPresenceUpdate.mock.calls[0][0];

    // Simulate receiving presence updates
    presenceCallback(mockUserPresence);

    await waitFor(() => {
      expect(screen.getByText('Sarah Chen')).toBeInTheDocument();
      expect(screen.getByText('Mike Johnson')).toBeInTheDocument();
      expect(screen.getByText('Alex Rodriguez')).toBeInTheDocument();
    });

    // Check status indicators
    expect(screen.getByText('Online')).toBeInTheDocument();
    expect(screen.getByText('Busy')).toBeInTheDocument();
    expect(screen.getByText('Away')).toBeInTheDocument();
  });

  it('should handle conflict alerts', async () => {
    render(
      <TestWrapper>
        <RealtimeDashboard />
      </TestWrapper>
    );

    // Wait for initial render
    await waitFor(() => {
      expect(mockOnConflictAlert).toHaveBeenCalled();
    });

    // Get the conflict alert callback
    const conflictCallback = mockOnConflictAlert.mock.calls[0][0];

    // Simulate receiving a conflict alert
    conflictCallback(mockConflicts[0]);

    await waitFor(() => {
      expect(screen.getByText('Merge Conflict Detected')).toBeInTheDocument();
      expect(screen.getByText('src/services/authService.ts')).toBeInTheDocument();
      expect(screen.getByText('Consider merging changes in a shared branch first')).toBeInTheDocument();
    });
  });

  it('should update stats based on real-time data', async () => {
    render(
      <TestWrapper>
        <RealtimeDashboard />
      </TestWrapper>
    );

    // Wait for initial render
    await waitFor(() => {
      expect(mockOnPresenceUpdate).toHaveBeenCalled();
    });

    // Simulate presence updates
    const presenceCallback = mockOnPresenceUpdate.mock.calls[0][0];
    presenceCallback(mockUserPresence);

    await waitFor(() => {
      // Should show 2 online users (online + busy)
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('of 3 total members')).toBeInTheDocument();
    });
  });

  it('should handle different layout modes', async () => {
    const { rerender } = render(
      <TestWrapper>
        <RealtimeDashboard layout="grid" />
      </TestWrapper>
    );

    // Check grid layout (default)
    await waitFor(() => {
      expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    });

    // Test sidebar layout
    rerender(
      <TestWrapper>
        <RealtimeDashboard layout="sidebar" />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Recent Activity')).toBeInTheDocument();
      expect(screen.getByText('Team Presence')).toBeInTheDocument();
    });

    // Test compact layout
    rerender(
      <TestWrapper>
        <RealtimeDashboard layout="compact" />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    });
  });

  it('should handle connection status changes', async () => {
    // Mock disconnected state
    vi.mocked(websocketService.isConnected).mockReturnValue(false);

    render(
      <TestWrapper>
        <RealtimeDashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Off')).toBeInTheDocument();
    });

    // Mock connected state
    vi.mocked(websocketService.isConnected).mockReturnValue(true);

    render(
      <TestWrapper>
        <RealtimeDashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Live')).toBeInTheDocument();
    });
  });

  it('should handle collaboration suggestions', async () => {
    render(
      <TestWrapper>
        <RealtimeDashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Collaboration Opportunities')).toBeInTheDocument();
    });

    // Check for mock suggestions (these are hardcoded in the component for now)
    expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    expect(screen.getByText('API integration expertise needed')).toBeInTheDocument();
  });

  it('should handle collaboration suggestion interactions', async () => {
    render(
      <TestWrapper>
        <RealtimeDashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    });

    // Find and click the "Connect" button for the first suggestion
    const connectButtons = screen.getAllByText('Connect');
    fireEvent.click(connectButtons[0]);

    // The suggestion should be removed after clicking Connect
    await waitFor(() => {
      expect(screen.queryByText('Similar component being developed')).not.toBeInTheDocument();
    });
  });

  it('should handle empty states gracefully', async () => {
    render(
      <TestWrapper>
        <RealtimeDashboard />
      </TestWrapper>
    );

    // Initially, there should be empty state messages
    await waitFor(() => {
      expect(screen.getByText('No recent activity')).toBeInTheDocument();
      expect(screen.getByText('No team members online')).toBeInTheDocument();
      expect(screen.getByText('No active conflicts')).toBeInTheDocument();
    });
  });
});