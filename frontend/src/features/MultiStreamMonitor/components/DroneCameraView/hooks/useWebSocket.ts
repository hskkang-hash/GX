import { useRef, useEffect, useState, useCallback } from 'react';

import { DrawingMessage } from '../types';

interface UseWebSocketProps {
  socketUrl: string;
  sessionId: string;
  userId: string;
  streamId: string;
  droneCode: string;
  onMessage: (message: DrawingMessage) => void;
}

export const useWebSocket = ({
  socketUrl,
  sessionId,
  userId,
  streamId,
  droneCode,
  onMessage,
}: UseWebSocketProps) => {
  const websocketRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const sendMessage = useCallback(
    (message: DrawingMessage) => {
      if (
        websocketRef.current &&
        websocketRef.current.readyState === WebSocket.OPEN &&
        isConnected
      ) {
        try {
          const jsonMessage = JSON.stringify(message);
          // Send 3 times to ensure websocket receives the message
          for (let i = 0; i < 3; i++) {
            websocketRef.current.send(jsonMessage);
          }
          console.log('📤 Sent drawing message (x3):', message.type, message);
        } catch (error) {
          console.error('Error sending drawing message:', error);
        }
      } else {
        console.warn('⚠️ Cannot send message - WebSocket not connected:', {
          websocket: !!websocketRef.current,
          readyState: websocketRef.current?.readyState,
          isConnected,
          socketUrl,
        });
      }
    },
    [isConnected, socketUrl],
  );

  useEffect(() => {
    if (!socketUrl) return;

    console.log('🔗 Attempting to connect to WebSocket:', socketUrl);

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(socketUrl);
        websocketRef.current = ws;

        ws.onopen = () => {
          console.log('✅ Connected to drawing WebSocket server:', socketUrl);
          setIsConnected(true);

          const joinMessage: DrawingMessage = {
            type: 'join',
            sessionId: sessionId,
            userId: userId,
            stream_id: streamId,
            drone_code: droneCode,
          };
          ws.send(JSON.stringify(joinMessage));
          console.log('📤 Sent join message:', joinMessage);

          // Request existing drawings after joining
          setTimeout(() => {
            const requestDrawingMessage: DrawingMessage = {
              type: 'request_drawing',
              sessionId: sessionId,
              userId: userId,
              stream_id: streamId,
              drone_code: droneCode,
            };
            ws.send(JSON.stringify(requestDrawingMessage));
            console.log(
              '📤 Requesting existing drawings:',
              requestDrawingMessage,
            );
          }, 500);
        };

        ws.onclose = (event) => {
          console.log(
            '❌ Disconnected from drawing WebSocket server',
            event.code,
            event.reason,
          );
          setIsConnected(false);

          setTimeout(() => {
            if (
              !websocketRef.current ||
              websocketRef.current.readyState === WebSocket.CLOSED
            ) {
              console.log('🔄 Attempting to reconnect to:', socketUrl);
              connectWebSocket();
            }
          }, 3000);
        };

        ws.onerror = (error) => {
          console.log('❌ WebSocket error connecting to:', socketUrl, error);
          setIsConnected(false);
        };

        ws.onmessage = (event) => {
          try {
            const message: DrawingMessage = JSON.parse(event.data);
            console.log('📥 Received WebSocket message:', message);

            if (message.userId !== undefined) {
              message.userId = String(message.userId);
            }

            if (
              (message.type === 'participant_joined' ||
                message.type === 'participant_left') &&
              String(message.userId) === String(userId)
            ) {
              console.log('🔄 Ignoring own participant message');
              return;
            }

            if (
              message.type === 'element_added' &&
              message.element &&
              message.element.created_by
            ) {
              if (
                message.element?.data?.created_by_id === String(userId) ||
                message.element?.data?.created_by_id === userId
              ) {
                console.log(
                  '🔄 Ignoring own drawing message from created_by:',
                  message.element.created_by,
                );
                return;
              }
            }

            onMessage(message);
          } catch (error) {
            console.log(
              '❌ Error parsing WebSocket message:',
              error,
              event.data,
            );
          }
        };
      } catch (error) {
        console.log(
          'Error creating WebSocket connection to:',
          socketUrl,
          error,
        );
        setIsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (websocketRef.current) {
        if (websocketRef.current.readyState === WebSocket.OPEN) {
          const leaveMessage: DrawingMessage = {
            type: 'leave',
            sessionId: sessionId,
            userId: userId,
            stream_id: streamId,
            drone_code: droneCode,
          };
          websocketRef.current.send(JSON.stringify(leaveMessage));
          console.log('📤 Sent leave message:', leaveMessage);
        }
        websocketRef.current.close();
        websocketRef.current = null;
        console.log('🔌 WebSocket connection closed');
      }
    };
  }, [socketUrl, sessionId, userId, streamId, droneCode, onMessage]);

  return { isConnected, sendMessage };
};
