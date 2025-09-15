import { io, Socket } from 'socket.io-client';

// Base URL for the API server; socket.io client will use the `path` option below
const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8000';

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

      // Try Socket.IO first
      this.socket = io(WS_URL, {
        auth: {
          token,
        },
        // Use polling-only for demo to avoid native websocket origin checks that can be blocked
        transports: ['polling'],
        upgrade: false,
        path: '/socket.io',
        timeout: 5000,
      });

      const onConnect = () => {
        console.log('WebSocket (socket.io) connected');
        this.reconnectAttempts = 0;
        cleanupListeners();
        resolve(this.socket!);
      };

      const onConnectError = (error: any) => {
        console.warn('Socket.IO connect error, falling back to native WebSocket:', error);
        cleanupListeners();
        // Attempt native WebSocket fallback
        try {
          const wsProto = WS_URL.startsWith('https') ? 'wss' : 'ws';
          // Connect to the backend WebSocket endpoint under /api/ws
          const url = `${wsProto}://${new URL(WS_URL).host}/api/ws?token=${encodeURIComponent(token)}`;
          const nativeWs = new WebSocket(url);

          // Minimal adapter that maps incoming messages to the same event handlers
          nativeWs.onopen = () => {
            console.log('Native WebSocket connected (fallback)');
            // Create a fake Socket-like wrapper with only necessary methods
            const fakeSocket: any = {
              connected: true,
              emit: (eventName: string, data?: any) => {
                const payload = JSON.stringify({ type: eventName, data });
                nativeWs.send(payload);
              },
              on: (eventName: string, cb: any) => {
                // map eventName to message types in incoming JSON
                // We'll store handlers on the fakeSocket
                (fakeSocket as any)._handlers = (fakeSocket as any)._handlers || {};
                (fakeSocket as any)._handlers[eventName] = cb;
              },
              off: (eventName: string, cb: any) => {
                (fakeSocket as any)._handlers = (fakeSocket as any)._handlers || {};
                delete (fakeSocket as any)._handlers[eventName];
              },
              disconnect: () => nativeWs.close(),
            };

            nativeWs.onmessage = (ev) => {
              try {
                const msg = JSON.parse(ev.data);
                // msg expected format: { type: 'presence:update', data: [...] }
                const handlers = (fakeSocket as any)._handlers || {};
                const handler = handlers[msg.type];
                if (handler) handler(msg.data);
                // also map some well-known events
                if (msg.type === 'presence:update' && this.socket) {
                  // if socket exists use the existing event emitter
                }
              } catch (e) {
                console.warn('Failed to parse WS message', e);
              }
            };

            nativeWs.onclose = (ev) => {
              console.log('Native WebSocket closed', ev);
            };

            nativeWs.onerror = (err) => {
              console.error('Native WebSocket error', err);
            };

            // Replace this.socket with the fakeSocket so rest of the app can use it
            (this as any).socket = fakeSocket;
            resolve((this as any).socket as Socket);
          };

          nativeWs.onerror = (err) => {
            console.error('Native WebSocket fallback failed', err);
            reject(err);
          };
        } catch (e) {
          console.error('Fallback connection failed', e);
          reject(e);
        }
      };

      const cleanupListeners = () => {
        this.socket?.off('connect', onConnect);
        this.socket?.off('connect_error', onConnectError);
      };

      this.socket.on('connect', onConnect);
      this.socket.on('connect_error', onConnectError);

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