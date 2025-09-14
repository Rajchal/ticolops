import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { RealtimeProvider, useRealtime } from '../../../contexts/RealtimeContext';
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

// Test component to access realtime context
const TestComponent: React.FC = () => {
  const {
    isConnected,
    activities,
    userPresence,
    conflicts,
    connectionError,
    updatePresence,
    joinProject,
    leaveProject,
    joinFile,
    leaveFile,
    dismissConflict,
    clearActivities,
  } = useRealtime();

  return (
    <div>
      <div data-testid="connection-status">{isConnected ? 'connected' : 'disconnected'}</div>
      <div data-testid="activities-count">{activities.length}</div>
      <div data-testid="presence-count">{userPresence.length}</div>
      <div data-testid="conflicts-count">{conflicts.length}</div>
      <div data-testid="connection-error">{connectionError || 'none'}</div>
      
      <button onClick={() => updatePresence('busy', { projectId: 'test-project' })}>
        Update Presence
      </button>
      <button onClick={() => joinProject('test-project')}>Join Project</button>
      <button onClick={() => leaveProject('test-project')}>Leave Project</button>
      <button onClick={() => joinFile('test-project', 'test-file.ts')}>Join File</button>
      <button onClick={() => leaveFile('test-project', 'test-file.ts')}>Leave File</button>
      <button onClick={() => dismissConflict('conflict-1')}>Dismiss Conflict</button>
      <button onClick={() => clearActivities()}>Clear Activities</button>
      
      <div data-testid="activities">
        {activities.map(activity => (
          <div key={activity.id} data-testid={`activity-${activity.id}`}>
            {activity.message}
          </div>
        ))}
      </div>
      
      <div data-testid="presence">
        {userPresence.map(user => (
          <div key={user.userId} data-testid={`user-${user.userId}`}>
            {user.userName} - {user.status}
          </div>
        ))}
      </div>
      
      <div data-testid="conflicts">
        {conflicts.map(conflict => (
          <div key={conflict.id} data-testid={`conflict-${conflict.id}`}>
            {conflict.type} - {conflict.severity}
          </div>
        ))}
      </div>
    </div>
  );
};

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>
    <RealtimeProvider>
      {children}
    </RealtimeProvider>
  </AuthProvider>
);

describe('WebSocket Integration Tests', () => {
  let mockConnect: any;
  let mockDisconnect: any;
  let mockOnActivityEvent: any;
  let mockOnPresenceUpdate: any;
  let mockOnConflictAlert: any;
  let mockOffActivityEvent: any;
  let mockOffPresenceUpdate: any;
  let mockOffConflictAlert: any;
  let mockUpdatePresence: any;
  let mockJoinProject: any;
  let mockLeaveProject: any;
  let mockJoinFile: any;
  let mockLeaveFile: any;

  beforeEach(() => {
    // Reset all mocks
    vi.clearAllMocks();
    
    // Setup websocket service mocks
    mockConnect = vi.mocked(websocketService.connect);
    mockDisconnect = vi.mocked(websocketService.disconnect);
    mockOnActivityEvent = vi.mocked(websocketService.onActivityEvent);
    mockOnPresenceUpdate = vi.mocked(websocketService.onPresenceUpdate);
    mockOnConflictAlert = vi.mocked(websocketService.onConflictAlert);
    mockOffActivityEvent = vi.mocked(websocketService.offActivityEvent);
    mockOffPresenceUpdate = vi.mocked(websocketService.offPresenceUpdate);
    mockOffConflictAlert = vi.mocked(websocketService.offConflictAlert);
    mockUpdatePresence = vi.mocked(websocketService.updatePresence);
    mockJoinProject = vi.mocked(websocketService.joinProject);
    mockLeaveProject = vi.mocked(websocketService.leaveProject);
    mockJoinFile = vi.mocked(websocketService.joinFile);
    mockLeaveFile = vi.mocked(websocketService.leaveFile);

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

  it('should establish WebSocket connection on mount', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockConnect).toHaveBeenCalledWith('mock-token');
      expect(mockOnActivityEvent).toHaveBeenCalled();
      expect(mockOnPresenceUpdate).toHaveBeenCalled();
      expect(mockOnConflictAlert).toHaveBeenCalled();
    });

    expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');
  });

  it('should handle connection errors', async () => {
    const connectionError = new Error('Connection failed');
    mockConnect.mockRejectedValue(connectionError);

    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByTestId('connection-status')).toHaveTextContent('disconnected');
      expect(screen.getByTestId('connection-error')).toHaveTextContent('Connection failed');
    });
  });

  it('should handle activity events', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockOnActivityEvent).toHaveBeenCalled();
    });

    // Get the activity event callback
    const activityCallback = mockOnActivityEvent.mock.calls[0][0];

    // Simulate receiving activity events
    const mockActivity: ActivityEvent = {
      id: 'activity-1',
      type: 'commit',
      userId: 'user-1',
      userName: 'Test User',
      projectId: 'proj-1',
      projectName: 'Test Project',
      message: 'Test commit message',
      timestamp: new Date(),
    };

    act(() => {
      activityCallback(mockActivity);
    });

    await waitFor(() => {
      expect(screen.getByTestId('activities-count')).toHaveTextContent('1');
      expect(screen.getByTestId('activity-activity-1')).toHaveTextContent('Test commit message');
    });
  });

  it('should handle presence updates', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockOnPresenceUpdate).toHaveBeenCalled();
    });

    // Get the presence update callback
    const presenceCallback = mockOnPresenceUpdate.mock.calls[0][0];

    // Simulate receiving presence updates
    const mockPresence: UserPresence[] = [
      {
        userId: 'user-1',
        userName: 'Test User 1',
        status: 'online',
        lastSeen: new Date(),
      },
      {
        userId: 'user-2',
        userName: 'Test User 2',
        status: 'busy',
        lastSeen: new Date(),
      },
    ];

    act(() => {
      presenceCallback(mockPresence);
    });

    await waitFor(() => {
      expect(screen.getByTestId('presence-count')).toHaveTextContent('2');
      expect(screen.getByTestId('user-user-1')).toHaveTextContent('Test User 1 - online');
      expect(screen.getByTestId('user-user-2')).toHaveTextContent('Test User 2 - busy');
    });
  });

  it('should handle conflict alerts', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockOnConflictAlert).toHaveBeenCalled();
    });

    // Get the conflict alert callback
    const conflictCallback = mockOnConflictAlert.mock.calls[0][0];

    // Simulate receiving conflict alerts
    const mockConflict: ConflictAlert = {
      id: 'conflict-1',
      type: 'merge_conflict',
      projectId: 'proj-1',
      projectName: 'Test Project',
      filePath: 'src/test.ts',
      users: ['user-1', 'user-2'],
      severity: 'high',
      suggestion: 'Test suggestion',
      timestamp: new Date(),
    };

    act(() => {
      conflictCallback(mockConflict);
    });

    await waitFor(() => {
      expect(screen.getByTestId('conflicts-count')).toHaveTextContent('1');
      expect(screen.getByTestId('conflict-conflict-1')).toHaveTextContent('merge_conflict - high');
    });
  });

  it('should handle presence updates', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockUpdatePresence).toHaveBeenCalledWith('online');
    });

    // Click update presence button
    const updateButton = screen.getByText('Update Presence');
    act(() => {
      updateButton.click();
    });

    expect(mockUpdatePresence).toHaveBeenCalledWith('busy', { projectId: 'test-project' });
  });

  it('should handle project join/leave', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    // Click join project button
    const joinButton = screen.getByText('Join Project');
    act(() => {
      joinButton.click();
    });

    expect(mockJoinProject).toHaveBeenCalledWith('test-project');
    expect(mockUpdatePresence).toHaveBeenCalledWith('online', { projectId: 'test-project' });

    // Click leave project button
    const leaveButton = screen.getByText('Leave Project');
    act(() => {
      leaveButton.click();
    });

    expect(mockLeaveProject).toHaveBeenCalledWith('test-project');
    expect(mockUpdatePresence).toHaveBeenCalledWith('online');
  });

  it('should handle file join/leave', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    // Click join file button
    const joinFileButton = screen.getByText('Join File');
    act(() => {
      joinFileButton.click();
    });

    expect(mockJoinFile).toHaveBeenCalledWith('test-project', 'test-file.ts');
    expect(mockUpdatePresence).toHaveBeenCalledWith('busy', { 
      projectId: 'test-project', 
      filePath: 'test-file.ts' 
    });

    // Click leave file button
    const leaveFileButton = screen.getByText('Leave File');
    act(() => {
      leaveFileButton.click();
    });

    expect(mockLeaveFile).toHaveBeenCalledWith('test-project', 'test-file.ts');
    expect(mockUpdatePresence).toHaveBeenCalledWith('online', { projectId: 'test-project' });
  });

  it('should handle conflict dismissal', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    // First add a conflict
    await waitFor(() => {
      expect(mockOnConflictAlert).toHaveBeenCalled();
    });

    const conflictCallback = mockOnConflictAlert.mock.calls[0][0];
    const mockConflict: ConflictAlert = {
      id: 'conflict-1',
      type: 'merge_conflict',
      projectId: 'proj-1',
      projectName: 'Test Project',
      filePath: 'src/test.ts',
      users: ['user-1', 'user-2'],
      severity: 'high',
      suggestion: 'Test suggestion',
      timestamp: new Date(),
    };

    act(() => {
      conflictCallback(mockConflict);
    });

    await waitFor(() => {
      expect(screen.getByTestId('conflicts-count')).toHaveTextContent('1');
    });

    // Click dismiss conflict button
    const dismissButton = screen.getByText('Dismiss Conflict');
    act(() => {
      dismissButton.click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('conflicts-count')).toHaveTextContent('0');
    });
  });

  it('should handle activity clearing', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    // First add an activity
    await waitFor(() => {
      expect(mockOnActivityEvent).toHaveBeenCalled();
    });

    const activityCallback = mockOnActivityEvent.mock.calls[0][0];
    const mockActivity: ActivityEvent = {
      id: 'activity-1',
      type: 'commit',
      userId: 'user-1',
      userName: 'Test User',
      projectId: 'proj-1',
      projectName: 'Test Project',
      message: 'Test commit message',
      timestamp: new Date(),
    };

    act(() => {
      activityCallback(mockActivity);
    });

    await waitFor(() => {
      expect(screen.getByTestId('activities-count')).toHaveTextContent('1');
    });

    // Click clear activities button
    const clearButton = screen.getByText('Clear Activities');
    act(() => {
      clearButton.click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('activities-count')).toHaveTextContent('0');
    });
  });

  it('should cleanup event listeners on unmount', async () => {
    const { unmount } = render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockOnActivityEvent).toHaveBeenCalled();
      expect(mockOnPresenceUpdate).toHaveBeenCalled();
      expect(mockOnConflictAlert).toHaveBeenCalled();
    });

    // Unmount the component
    unmount();

    // Check that cleanup functions were called
    expect(mockOffActivityEvent).toHaveBeenCalled();
    expect(mockOffPresenceUpdate).toHaveBeenCalled();
    expect(mockOffConflictAlert).toHaveBeenCalled();
    expect(mockDisconnect).toHaveBeenCalled();
  });

  it('should handle visibility change events', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockUpdatePresence).toHaveBeenCalledWith('online');
    });

    // Simulate page becoming hidden
    Object.defineProperty(document, 'hidden', {
      writable: true,
      value: true,
    });

    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    expect(mockUpdatePresence).toHaveBeenCalledWith('away');

    // Simulate page becoming visible again
    Object.defineProperty(document, 'hidden', {
      writable: true,
      value: false,
    });

    act(() => {
      document.dispatchEvent(new Event('visibilitychange'));
    });

    expect(mockUpdatePresence).toHaveBeenCalledWith('online');
  });

  it('should handle beforeunload events', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockUpdatePresence).toHaveBeenCalledWith('online');
    });

    // Simulate beforeunload event
    act(() => {
      window.dispatchEvent(new Event('beforeunload'));
    });

    expect(mockUpdatePresence).toHaveBeenCalledWith('offline');
  });

  it('should limit activities to 50 items', async () => {
    render(
      <TestWrapper>
        <TestComponent />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockOnActivityEvent).toHaveBeenCalled();
    });

    const activityCallback = mockOnActivityEvent.mock.calls[0][0];

    // Add 60 activities
    for (let i = 0; i < 60; i++) {
      const mockActivity: ActivityEvent = {
        id: `activity-${i}`,
        type: 'commit',
        userId: 'user-1',
        userName: 'Test User',
        projectId: 'proj-1',
        projectName: 'Test Project',
        message: `Test commit message ${i}`,
        timestamp: new Date(),
      };

      act(() => {
        activityCallback(mockActivity);
      });
    }

    await waitFor(() => {
      // Should only keep the last 50 activities
      expect(screen.getByTestId('activities-count')).toHaveTextContent('50');
    });
  });
});