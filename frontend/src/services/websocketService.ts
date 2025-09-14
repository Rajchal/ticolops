import { io, Socket } from 'socket.io-client';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export interface ActivityEvent {
  id: string;
  type: 'commit' | 'deployment' | 'collaboration' | 'conflict' | 'presence';
  userId: string;
  userName: string;
  userAvatar?: string;
  projectId: string;
  projectName: string;
  message: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface UserPresence {
  userId: string;
  userName: string;
  userAvatar?: string;
  status: 'online' | 'away' | 'busy' | 'offline';
  currentProject?: string;
  currentFile?: string;
  lastSeen: Date;
}

export interface ConflictAlert {
  id: string;
  type: 'merge_conflict' | 'file_lock' | 'simultaneous_edit';
  projectId: string;
  projectName: string;
  filePath: string;
  users: string[];
  severity: 'low' | 'medium' | 'high';
  suggestion: string;
  timestamp: Date;
}

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(token: string): Promise<Socket> {
    return new Promise((resolve, reject) => {
      if (this.socket?.connected) {
        resolve(this.socket);
        return;
      }

      this.socket = io(WS_URL, {
        auth: {
          token,
        },
        transports: ['websocket', 'polling'],
      });

      this.socket.on('connect', () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        resolve(this.socket!);
      });

      this.socket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
        reject(error);
      });

      this.socket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason);
        if (reason === 'io server disconnect') {
          // Server disconnected, try to reconnect
          this.handleReconnect();
        }
      });

      this.socket.on('reconnect_attempt', (attemptNumber) => {
        console.log(`WebSocket reconnect attempt ${attemptNumber}`);
      });

      this.socket.on('reconnect', (attemptNumber) => {
        console.log(`WebSocket reconnected after ${attemptNumber} attempts`);
        this.reconnectAttempts = 0;
      });

      this.socket.on('reconnect_failed', () => {
        console.error('WebSocket reconnection failed');
      });
    });
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.socket?.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  // Activity events
  onActivityEvent(callback: (event: ActivityEvent) => void) {
    this.socket?.on('activity:new', callback);
  }

  offActivityEvent(callback: (event: ActivityEvent) => void) {
    this.socket?.off('activity:new', callback);
  }

  // User presence
  onPresenceUpdate(callback: (users: UserPresence[]) => void) {
    this.socket?.on('presence:update', callback);
  }

  offPresenceUpdate(callback: (users: UserPresence[]) => void) {
    this.socket?.off('presence:update', callback);
  }

  updatePresence(status: UserPresence['status'], metadata?: { projectId?: string; filePath?: string }) {
    this.socket?.emit('presence:update', { status, ...metadata });
  }

  // Conflict detection
  onConflictAlert(callback: (conflict: ConflictAlert) => void) {
    this.socket?.on('conflict:alert', callback);
  }

  offConflictAlert(callback: (conflict: ConflictAlert) => void) {
    this.socket?.off('conflict:alert', callback);
  }

  // Project collaboration
  joinProject(projectId: string) {
    this.socket?.emit('project:join', { projectId });
  }

  leaveProject(projectId: string) {
    this.socket?.emit('project:leave', { projectId });
  }

  // File collaboration
  joinFile(projectId: string, filePath: string) {
    this.socket?.emit('file:join', { projectId, filePath });
  }

  leaveFile(projectId: string, filePath: string) {
    this.socket?.emit('file:leave', { projectId, filePath });
  }

  // Typing indicators
  onTypingStart(callback: (data: { userId: string; userName: string; filePath: string }) => void) {
    this.socket?.on('typing:start', callback);
  }

  onTypingStop(callback: (data: { userId: string; filePath: string }) => void) {
    this.socket?.on('typing:stop', callback);
  }

  emitTypingStart(filePath: string) {
    this.socket?.emit('typing:start', { filePath });
  }

  emitTypingStop(filePath: string) {
    this.socket?.emit('typing:stop', { filePath });
  }

  getSocket(): Socket | null {
    return this.socket;
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }
}

export const websocketService = new WebSocketService();