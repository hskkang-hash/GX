import { useEffect, useRef, useState, useCallback } from 'react';

type PartnerCallbackType =
  | 'delivery_status_callback'
  | 'drone_base_station_callback'
  | 'drone_user_notice_callback'
  | 'partner_callback_error'
  | 'connected';

type PartnerCallbackMessage = {
  type: PartnerCallbackType;
  timestamp?: string;
  callback_type?: string;
  data?: {
    serviceKey?: string;
    itemOrgId?: string;
    deliveryStatus?: string;
    startDeliveryPoint?: string;
    status?: string;
    BCode?: string;
    IsNotice?: number;
    Html1?: string;
    message?: string | number;
    updateTime?: string;
  };
  partner_info?: {
    callback_type?: string;
    serviceKey_prefix?: string;
    received_at?: string;
  };
  success?: boolean;
  message?: string;
  user?: string;
  error?: string;
};

export const usePartnerCallbackWebSocket = ({
  socketUrl,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
  heartbeatInterval = 30000,
}: {
  socketUrl: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}): {
  isConnected: boolean;
  message: PartnerCallbackMessage | null;
  clearMessage: () => void;
  reconnectAttempts: number;
} => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [message, setMessage] = useState<PartnerCallbackMessage | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState<number>(0);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef<boolean>(true);
  const reconnectAttemptsRef = useRef<number>(0);

  const clearMessage = () => {
    setMessage(null);
  };

  // Clear timeouts
  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  // Start heartbeat
  const startHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }
    heartbeatTimeoutRef.current = setTimeout(() => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        try {
          socketRef.current.send(JSON.stringify({ type: 'ping' }));
          console.log('💓 Heartbeat sent');
          startHeartbeat(); // Schedule next heartbeat
        } catch (error) {
          console.error('💓 Heartbeat failed:', error);
        }
      }
    }, heartbeatInterval);
  }, [heartbeatInterval]);

  // Connect function
  const connect = useCallback(() => {
    if (!socketUrl || !shouldReconnectRef.current) {
      return;
    }

    // Close existing connection if any
    if (socketRef.current) {
      socketRef.current.close();
    }

    console.log(
      `🔄 Attempting to connect... (Attempt ${reconnectAttemptsRef.current + 1})`,
    );

    const socket = new WebSocket(socketUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      reconnectAttemptsRef.current = 0;
      setReconnectAttempts(0);
      console.log('🔗 Connected to partner callback notifications');
      startHeartbeat();
    };

    socket.onmessage = (event: MessageEvent): void => {
      const dataRaw = event.data;
      console.log('🎯 [DEBUG] Raw WebSocket message received:', dataRaw);

      try {
        const parsed =
          typeof dataRaw === 'string' ? JSON.parse(dataRaw) : dataRaw;
        console.log('🎯 [DEBUG] Parsed WebSocket message:', parsed);

        // Handle pong response
        if (parsed?.type === 'pong') {
          console.log('💓 Pong received');
          return;
        }

        if (parsed) {
          console.log('📨 Partner callback received:', parsed);

          // Chỉ hiển thị popup cho các callback thực tế, không phải connection messages
          if (parsed.type !== 'connected') {
            console.log('🎯 [DEBUG] Setting message for popup:', parsed);
            setMessage(parsed as PartnerCallbackMessage);
          } else {
            console.log('🎯 [DEBUG] Skipping connected message');
          }
        }
      } catch (error) {
        console.error('❌ Error parsing partner callback message:', error);
        setMessage({
          type: 'partner_callback_error',
          error: 'Failed to parse message',
          message: 'Invalid message format received',
        } as PartnerCallbackMessage);
      }
    };

    socket.onclose = (event) => {
      setIsConnected(false);
      clearTimeouts();
      socketRef.current = null;
      console.log('❌ Disconnected from partner callback notifications', event);

      // Only auto-reconnect if page is visible and should reconnect
      if (
        shouldReconnectRef.current &&
        reconnectAttemptsRef.current < maxReconnectAttempts &&
        !document.hidden
      ) {
        const delay = Math.min(
          reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current),
          30000,
        );
        console.log(`🔄 Reconnecting in ${delay}ms...`);

        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttemptsRef.current += 1;
          setReconnectAttempts(reconnectAttemptsRef.current);
          connect();
        }, delay);
      } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
        console.error('🚨 Max reconnection attempts reached');
      } else if (document.hidden) {
        console.log('🔄 Page hidden, skipping reconnection');
      }
    };

    socket.onerror = (error) => {
      setIsConnected(false);
      console.error('🚨 Partner callback WebSocket error:', error);
    };
  }, [
    socketUrl,
    maxReconnectAttempts,
    reconnectInterval,
    startHeartbeat,
    clearTimeouts,
  ]);

  useEffect(() => {
    if (!socketUrl) {
      setIsConnected(false);
      setMessage(null);
      return;
    }

    shouldReconnectRef.current = true;
    reconnectAttemptsRef.current = 0;
    connect();

    // Handle page visibility changes
    const handleVisibilityChange = () => {
      if (document.hidden) {
        console.log('🔄 Page hidden, pausing WebSocket operations');
        shouldReconnectRef.current = false;
        clearTimeouts();
      } else {
        console.log('🔄 Page visible, resuming WebSocket operations');
        shouldReconnectRef.current = true;
        if (
          !socketRef.current ||
          socketRef.current.readyState === WebSocket.CLOSED
        ) {
          reconnectAttemptsRef.current = 0;
          setReconnectAttempts(0);
          connect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      shouldReconnectRef.current = false;
      clearTimeouts();
      document.removeEventListener('visibilitychange', handleVisibilityChange);

      try {
        if (socketRef.current) {
          socketRef.current.close();
          socketRef.current = null;
          console.log('🔌 Partner callback WebSocket closed');
        }
      } catch {
        // no-op
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [socketUrl]);

  return { isConnected, message, clearMessage, reconnectAttempts };
};
