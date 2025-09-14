import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { websocketService, type ActivityEvent, type UserPresence, type ConflictAlert } from '../services/websocketService';
import { useAuth } from './AuthContext';

interface RealtimeContextType {
  isConnected: boolean;
  activities: ActivityEvent[];
  userPresence: UserPresence[];
  conflicts: ConflictAlert[];
  connectionError: string | null;
  updatePresence: (status: UserPresence['status'], metadata?: { projectId?: string; filePath?: string }) => void;
  joinProject: (projectId: string) => void;
  leaveProject: (projectId: string) => void;
  joinFile: (projectId: string, filePath: string) => void;
  leaveFile: (projectId: string, filePath: string) => void;
  dismissConflict: (conflictId: string) => void;
  clearActivities: () => void;
}

const RealtimeContext = createContext<RealtimeContextType | undefined>(undefined);

export const useRealtime = () => {
  const context = useContext(RealtimeContext);
  if (context === undefined) {
    throw new Error('useRealtime must be used within a RealtimeProvider');
  }
  return context;
};

interface RealtimeProviderProps {
  children: ReactNode;
}

export const RealtimeProvider: React.FC<RealtimeProviderProps> = ({ children }) => {
  const { user } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [activities, setActivities] = useState<ActivityEvent[]>([]);
  const [userPresence, setUserPresence] = useState<UserPresence[]>([]);
  const [conflicts, setConflicts] = useState<ConflictAlert[]>([]);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      // Disconnect when user logs out
      websocketService.disconnect();
      setIsConnected(false);
      setActivities([]);
      setUserPresence([]);
      setConflicts([]);
      setConnectionError(null);
      return;
    }

    const connectWebSocket = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No authentication token found');
        }

        await websocketService.connect(token);
        setIsConnected(true);
        setConnectionError(null);

        // Set up event listeners
        const handleActivityEvent = (event: ActivityEvent) => {
          setActivities(prev => [event, ...prev.slice(0, 49)]); // Keep last 50 activities
        };

        const handlePresenceUpdate = (users: UserPresence[]) => {
          setUserPresence(users);
        };

        const handleConflictAlert = (conflict: ConflictAlert) => {
          setConflicts(prev => [conflict, ...prev]);
        };

        websocketService.onActivityEvent(handleActivityEvent);
        websocketService.onPresenceUpdate(handlePresenceUpdate);
        websocketService.onConflictAlert(handleConflictAlert);

        // Set initial presence
        websocketService.updatePresence('online');

        // Cleanup function
        return () => {
          websocketService.offActivityEvent(handleActivityEvent);
          websocketService.offPresenceUpdate(handlePresenceUpdate);
          websocketService.offConflictAlert(handleConflictAlert);
        };
      } catch (error) {
        console.error('Failed to connect to WebSocket:', error);
        setConnectionError(error instanceof Error ? error.message : 'Connection failed');
        setIsConnected(false);
      }
    };

    const cleanup = connectWebSocket();

    // Cleanup on unmount
    return () => {
      cleanup?.then(cleanupFn => cleanupFn?.());
      websocketService.disconnect();
    };
  }, [user]);

  // Update presence when user becomes active/inactive
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        websocketService.updatePresence('away');
      } else {
        websocketService.updatePresence('online');
      }
    };

    const handleBeforeUnload = () => {
      websocketService.updatePresence('offline');
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  const updatePresence = (status: UserPresence['status'], metadata?: { projectId?: string; filePath?: string }) => {
    websocketService.updatePresence(status, metadata);
  };

  const joinProject = (projectId: string) => {
    websocketService.joinProject(projectId);
    websocketService.updatePresence('online', { projectId });
  };

  const leaveProject = (projectId: string) => {
    websocketService.leaveProject(projectId);
    websocketService.updatePresence('online');
  };

  const joinFile = (projectId: string, filePath: string) => {
    websocketService.joinFile(projectId, filePath);
    websocketService.updatePresence('busy', { projectId, filePath });
  };

  const leaveFile = (projectId: string, filePath: string) => {
    websocketService.leaveFile(projectId, filePath);
    websocketService.updatePresence('online', { projectId });
  };

  const dismissConflict = (conflictId: string) => {
    setConflicts(prev => prev.filter(conflict => conflict.id !== conflictId));
  };

  const clearActivities = () => {
    setActivities([]);
  };

  const value = {
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
  };

  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>;
};