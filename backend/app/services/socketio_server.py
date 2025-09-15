import logging
import asyncio
import socketio

logger = logging.getLogger(__name__)

# Create an Async Socket.IO server with permissive CORS for local dev
# Enable logging on the socketio/engineio side to help debug connection rejections
# cors_allowed_origins='*' allows all origins for local dev.
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*', logger=True, engineio_logger=True)


@sio.event
async def connect(sid, environ, auth):
    # Log detailed environ keys for debugging origin/headers during handshake
    origin = environ.get('HTTP_ORIGIN') or environ.get('origin')
    path = environ.get('PATH_INFO')
    logger.info("Socket.IO connect attempt: sid=%s origin=%s path=%s auth=%s", sid, origin, path, auth)
    # Accept connection for demo purposes
    return True


@sio.event
async def disconnect(sid):
    logger.info("Socket.IO disconnect: %s", sid)


@sio.on('project:join')
async def handle_join(sid, data):
    project_id = data.get('projectId') if isinstance(data, dict) else None
    logger.info("Socket.IO join: %s -> project %s", sid, project_id)
    if project_id:
        await sio.save_session(sid, {'project_id': project_id})
        await sio.enter_room(sid, project_id)
        # Broadcast a presence:update to the room as a simple demo
        await sio.emit('presence:update', [{'userId': sid, 'userName': 'Demo', 'status': 'online'}], room=project_id)


@sio.on('project:leave')
async def handle_leave(sid, data):
    project_id = data.get('projectId') if isinstance(data, dict) else None
    logger.info("Socket.IO leave: %s -> project %s", sid, project_id)
    if project_id:
        await sio.leave_room(sid, project_id)


@sio.on('presence:update')
async def handle_presence_update(sid, data):
    # Simply broadcast presence updates back to all clients (demo-only)
    logger.info('Socket.IO presence:update from %s: %s', sid, data)
    await sio.emit('presence:update', data, broadcast=True)


# ASGI app to mount
socketio_app = socketio.ASGIApp(sio)
