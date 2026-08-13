import { useCallback, useEffect, useRef, useState } from 'react';

import { calculateRelativeTime } from '../utils/mockRealtimeNotifications';
import { AbnormalSignMessage } from './useSurveillanceDashboard';

/**
 * WebSocket message structure from backend
 * Sent by MediaDetectConsumer.media_detect_notification
 */
interface WebSocketDetectionMessage {
  type: 'media_detect' | 'connected' | 'pong';
  msg?: string;
  data?: any[]; // Detection frames/data
  timestamp?: string;
}

interface UseAbnormalSignsWebSocketOptions {
  /**
   * Group code from userInfo.group_code
   * Used to connect to group-specific WebSocket room
   */
  groupCode?: string;

  /**
   * Whether to enable WebSocket connection
   * Should be true when API returns status === "realtime"
   */
  enabled: boolean;

  /**
   * Callback when new abnormal sign message is received
   */
  onMessage: (message: AbnormalSignMessage) => void;

  /**
   * Base WebSocket URL (e.g., 'ws://localhost:8000' or 'wss://api.example.com')
   */
  wsBaseUrl?: string;
}

/**
 * Custom hook for managing WebSocket connection to receive real-time abnormal signs.
 *
 * **When to use:**
 * - Use this hook when the API returns `status === "realtime"`
 * - This means the backend is actively processing detections and will push updates
 *
 * **How it works:**
 * 1. Connects to `ws://[host]/ws/media/detect/` WebSocket endpoint
 * 2. Backend sends messages to `{group_code}` channel when detections occur
 * 3. MediaDetectConsumer forwards messages to connected clients
 * 4. Hook receives messages and calls `onMessage` callback
 *
 * **Backend flow:**
 * - `detect_callback` API receives detection results
 * - Sends to channel: `channel_layer.group_send(group_code, {...})`
 * - MediaDetectConsumer broadcasts to WebSocket clients
 *
 * @example
 * ```tsx
 * const { isConnected } = useAbnormalSignsWebSocket({
 *   groupCode: userInfo.group_code,
 *   enabled: notificationStatus === 'realtime',
 *   onMessage: (message) => {
 *     // Add new message to notifications list
 *     setNotifications(prev => [message, ...prev]);
 *   }
 * });
 * ```
 */
export const useAbnormalSignsWebSocket = ({
  groupCode,
  enabled,
  onMessage,
  wsBaseUrl,
}: UseAbnormalSignsWebSocketOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);

  // Keep onMessage ref updated
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  /**
   * Transform backend detection message to AbnormalSignMessage format
   */
  const transformMessage = useCallback(
    (data: WebSocketDetectionMessage): AbnormalSignMessage | null => {
      // Skip non-detection messages
      if (data.type !== 'media_detect') {
        return null;
      }

      // Extract detection data from the first item in the data array
      const detectionData = data.data && data.data[0];

      const timestamp = data.timestamp || new Date().toISOString();

      // Transform detection data to notification message
      return {
        id: `ws-${Date.now()}-${Math.random()}`, // Generate unique ID
        timestamp,
        category: 'warning', // Default category, adjust based on detection type
        message: data.msg || 'New abnormal sign detected',
        icon_type: 'warning', // Default icon type
        relative_time: calculateRelativeTime(timestamp), // Calculate based on timestamp
        // Extract image and location data if available
        detected_image_path: detectionData?.detected_image_path,
        drone_location: detectionData?.drone_location,
        detection_count: detectionData?.detection_count,
      };
    },
    [],
  );

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data: WebSocketDetectionMessage = JSON.parse(event.data);

        console.log('[ABNORMAL_SIGNS][WS] Received message:', data);

        // Handle connection confirmation
        if (data.type === 'connected') {
          console.log('[ABNORMAL_SIGNS][WS] Connected successfully');
          return;
        }

        // Handle detection messages
        if (data.type === 'media_detect') {
          const message = transformMessage(data);
          if (message) {
            onMessageRef.current(message);
          }
        }
      } catch (error) {
        console.error('[ABNORMAL_SIGNS][WS] Failed to parse message:', error);
      }
    },
    [transformMessage],
  );

  /**
   * Manage WebSocket connection lifecycle
   */
  useEffect(() => {
    console.log('enabled', enabled);
    console.log('groupCode', groupCode);
    // Don't connect if disabled or no group code
    if (!enabled || !groupCode) {
      setIsConnected(false);
      return () => {};
    }

    const wsUrl = `${import.meta.env.VITE_STREAMING_WS}/ws/media/detect/`;

    console.log('[ABNORMAL_SIGNS][WS] Connecting to:', wsUrl);

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      console.log('[ABNORMAL_SIGNS][WS] Connection opened');

      // Send ping to keep connection alive (optional)
      const pingInterval = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000); // Ping every 30 seconds

      // Store interval ID for cleanup
      (socket as any)._pingInterval = pingInterval;
    };

    socket.onmessage = handleMessage;

    socket.onclose = () => {
      setIsConnected(false);
      socketRef.current = null;
      console.log('[ABNORMAL_SIGNS][WS] Connection closed');

      // Clear ping interval
      if ((socket as any)._pingInterval) {
        clearInterval((socket as any)._pingInterval);
      }
    };

    socket.onerror = (error) => {
      setIsConnected(false);
      console.error('[ABNORMAL_SIGNS][WS] Connection error:', error);
    };

    // Cleanup on unmount or when dependencies change
    return () => {
      try {
        if ((socket as any)._pingInterval) {
          clearInterval((socket as any)._pingInterval);
        }

        if (socketRef.current) {
          socketRef.current.close();
          socketRef.current = null;
        } else {
          socket.close();
        }
      } catch (error) {
        console.error('[ABNORMAL_SIGNS][WS] Cleanup error:', error);
      }
    };
  }, [enabled, groupCode, wsBaseUrl, handleMessage]);

  return { isConnected };
};
