import { useCallback, useEffect, useRef, useState } from 'react';

interface WebSocketMessage {
  type: string;
  order_item_id?: number;
  order_item_ids?: number[];
  status: string;
  device_type?: string;
  notification_type?: string;
  message?: string;
  data?: {
    filename: string;
    download_url: string;
  };
}

interface UseWebSocketOptions {
  url: string;
  onMessage: (message: WebSocketMessage) => void;
}

export const useWebSocket = ({ url, onMessage }: UseWebSocketOptions) => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const socketRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);

  // Keep the ref updated with the latest onMessage function
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const handleMessage = useCallback((event: MessageEvent): void => {
    try {
      const data = JSON.parse(event.data);
      if (data.type !== 'connected') {
        onMessageRef.current(data);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }, []);

  useEffect((): (() => void) => {
    if (!url) {
      setIsConnected(false);
      return () => {};
    }

    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    socket.onmessage = handleMessage;

    socket.onclose = () => {
      setIsConnected(false);
      socketRef.current = null;
      console.log('WebSocket closed');
    };

    socket.onerror = (error) => {
      setIsConnected(false);
      console.error('WebSocket error:', error);
    };

    return () => {
      try {
        if (socketRef.current) {
          socketRef.current.close();
          socketRef.current = null;
        } else {
          socket.close();
        }
      } catch {
        // no-op
      }
    };
  }, [url, handleMessage]);

  return { isConnected };
};
