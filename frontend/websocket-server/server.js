const { createServer } = require('http');
const { Server } = require('socket.io');
const cors = require('cors');

const httpServer = createServer();
const io = new Server(httpServer, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST'],
  },
});

// Store active rooms and users
const rooms = new Map();
const users = new Map();

io.on('connection', (socket) => {
  console.log('User connected:', socket.id);

  // Join camera room
  socket.on('join_room', (data) => {
    const { cameraId, userId } = data;
    const roomName = `camera_${cameraId}`;

    socket.join(roomName);
    users.set(socket.id, { userId, cameraId, roomName });

    if (!rooms.has(roomName)) {
      rooms.set(roomName, new Set());
    }
    rooms.get(roomName).add(socket.id);

    // Notify other users in the room
    socket.to(roomName).emit('user_joined', { userId, cameraId });

    console.log(`User ${userId} joined camera room ${cameraId}`);
  });

  // Leave camera room
  socket.on('leave_room', (data) => {
    const { cameraId, userId } = data;
    const roomName = `camera_${cameraId}`;

    socket.leave(roomName);

    if (rooms.has(roomName)) {
      rooms.get(roomName).delete(socket.id);
      if (rooms.get(roomName).size === 0) {
        rooms.delete(roomName);
      }
    }

    // Notify other users in the room
    socket.to(roomName).emit('user_left', { userId, cameraId });

    console.log(`User ${userId} left camera room ${cameraId}`);
  });

  // Handle drawing actions
  socket.on('drawing_action', (action) => {
    const roomName = `camera_${action.cameraId}`;

    // Broadcast to all users in the room except sender
    socket.to(roomName).emit('drawing_action', action);

    console.log(`Drawing action from ${action.userId} in camera ${action.cameraId}`);
  });

  // Handle clear drawings
  socket.on('clear_drawings', (data) => {
    const { cameraId, userId } = data;
    const roomName = `camera_${cameraId}`;

    // Broadcast to all users in the room
    io.to(roomName).emit('clear_drawings', { cameraId, userId });

    console.log(`Clear drawings by ${userId} in camera ${cameraId}`);
  });

  // Handle disconnect
  socket.on('disconnect', () => {
    const userData = users.get(socket.id);
    if (userData) {
      const { userId, cameraId, roomName } = userData;

      if (rooms.has(roomName)) {
        rooms.get(roomName).delete(socket.id);
        if (rooms.get(roomName).size === 0) {
          rooms.delete(roomName);
        }
      }

      // Notify other users in the room
      socket.to(roomName).emit('user_left', { userId, cameraId });

      users.delete(socket.id);
      console.log(`User ${userId} disconnected from camera ${cameraId}`);
    }

    console.log('User disconnected:', socket.id);
  });
});

const PORT = process.env.PORT || 3001;

httpServer.listen(PORT, () => {
  console.log(`WebSocket server running on port ${PORT}`);
  console.log(`CORS enabled for all origins`);
});
