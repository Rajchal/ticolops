import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { websocketService } from '../websocketService';

// Mock socket.io-client
const mockSocket = {
    connected: false,
    connect: vi.fn(),
    disconnect: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
};

vi.mock('socket.io-client', () => ({
    io: vi.fn(() => mockSocket),
}));

describe('WebSocketService', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockSocket.connected = false;
    });

    afterEach(() => {
        websocketService.disconnect();
    });

    describe('connect', () => {
        it('should create socket connection with token', async () => {
            const token = 'test-token';
            mockSocket.connected = true;

            // Simulate successful connection
            setTimeout(() => {
                const connectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'connect')?.[1];
                if (connectHandler) connectHandler();
            }, 0);

            const socket = await websocketService.connect(token);
            expect(socket).toBeDefined();
            expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function));
        });

        it('should handle connection errors', async () => {
            const token = 'test-token';
            const error = new Error('Connection failed');

            // Simulate connection error
            setTimeout(() => {
                const errorHandler = mockSocket.on.mock.calls.find(call => call[0] === 'connect_error')?.[1];
                if (errorHandler) errorHandler(error);
            }, 0);

            await expect(websocketService.connect(token)).rejects.toThrow('Connection failed');
        });

        it('should return existing socket if already connected', async () => {
            mockSocket.connected = true;
            const token = 'test-token';

            const socket1 = await websocketService.connect(token);
            const socket2 = await websocketService.connect(token);

            expect(socket1).toBe(socket2);
        });
    });

    describe('disconnect', () => {
        it('should disconnect socket', () => {
            websocketService.disconnect();
            expect(mockSocket.disconnect).toHaveBeenCalled();
        });
    });

    describe('event handling', () => {
        it('should register activity event listener', () => {
            const callback = vi.fn();
            websocketService.onActivityEvent(callback);
            expect(mockSocket.on).toHaveBeenCalledWith('activity:new', callback);
        });

        it('should unregister activity event listener', () => {
            const callback = vi.fn();
            websocketService.offActivityEvent(callback);
            expect(mockSocket.off).toHaveBeenCalledWith('activity:new', callback);
        });

        it('should register presence update listener', () => {
            const callback = vi.fn();
            websocketService.onPresenceUpdate(callback);
            expect(mockSocket.on).toHaveBeenCalledWith('presence:update', callback);
        });

        it('should emit presence update', () => {
            const status = 'online';
            const metadata = { projectId: 'test-project' };
            websocketService.updatePresence(status, metadata);
            expect(mockSocket.emit).toHaveBeenCalledWith('presence:update', { status, ...metadata });
        });
    });

    describe('project collaboration', () => {
        it('should join project', () => {
            const projectId = 'test-project';
            websocketService.joinProject(projectId);
            expect(mockSocket.emit).toHaveBeenCalledWith('project:join', { projectId });
        });

        it('should leave project', () => {
            const projectId = 'test-project';
            websocketService.leaveProject(projectId);
            expect(mockSocket.emit).toHaveBeenCalledWith('project:leave', { projectId });
        });

        it('should join file', () => {
            const projectId = 'test-project';
            const filePath = 'src/test.js';
            websocketService.joinFile(projectId, filePath);
            expect(mockSocket.emit).toHaveBeenCalledWith('file:join', { projectId, filePath });
        });

        it('should leave file', () => {
            const projectId = 'test-project';
            const filePath = 'src/test.js';
            websocketService.leaveFile(projectId, filePath);
            expect(mockSocket.emit).toHaveBeenCalledWith('file:leave', { projectId, filePath });
        });
    });

    describe('typing indicators', () => {
        it('should emit typing start', () => {
            const filePath = 'src/test.js';
            websocketService.emitTypingStart(filePath);
            expect(mockSocket.emit).toHaveBeenCalledWith('typing:start', { filePath });
        });

        it('should emit typing stop', () => {
            const filePath = 'src/test.js';
            websocketService.emitTypingStop(filePath);
            expect(mockSocket.emit).toHaveBeenCalledWith('typing:stop', { filePath });
        });
    });

    describe('utility methods', () => {
        it('should return socket instance', () => {
            const socket = websocketService.getSocket();
            expect(socket).toBe(mockSocket);
        });

        it('should return connection status', () => {
            mockSocket.connected = true;
            expect(websocketService.isConnected()).toBe(true);

            mockSocket.connected = false;
            expect(websocketService.isConnected()).toBe(false);
        });
    });
});