// socketManager.ts
import io, { Socket } from 'socket.io-client';

class SocketManager {
  private static instance: SocketManager;
  private socket: Socket | null = null;
  private url: string = '';

  private constructor() {}

  static getInstance(): SocketManager {
    if (!SocketManager.instance) {
      SocketManager.instance = new SocketManager();
    }
    return SocketManager.instance;
  }

  connect(url: string): Socket {
    // If already connected to same URL, return existing socket
    if (this.socket && this.url === url && this.socket.connected) {
      return this.socket;
    }

    // If connected to different URL, disconnect first
    if (this.socket && this.url !== url) {
      this.socket.disconnect();
      this.socket = null;
    }

    // Create new connection if needed
    if (!this.socket) {
      this.url = url;
      this.socket = io(url, {
        transports: ['websocket'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 5,
      });

      this.socket.on('connect', () => {
        console.log('Socket connected:', this.socket?.id);
      });

      this.socket.on('disconnect', () => {
        console.log('Socket disconnected');
      });

      this.socket.on('error', (error) => {
        console.error('Socket error:', error);
      });
    }

    return this.socket;
  }

  getSocket(): Socket | null {
    return this.socket;
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.url = '';
    }
  }
}

export default SocketManager.getInstance();
