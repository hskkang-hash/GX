import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

type NewOrderMessage = {
  type: string;
  order_code: string;
  sender_name?: string;
  recipient_name?: string;
  created_on?: string;
  [key: string]: any;
};

type NotificationCallback = (data: {
  title: string;
  message: string;
  orderData: NewOrderMessage;
}) => void;

export const useNewOrderNotification = ({
  socketUrl,
  onNotification,
}: {
  socketUrl: string;
  onNotification?: NotificationCallback;
}): { isConnected: boolean } => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const socketRef = useRef<WebSocket | null>(null);
  const { t } = useTranslation();

  useEffect((): (() => void) => {
    if (!socketUrl) {
      setIsConnected(false);
      return () => {};
    }

    const socket = new WebSocket(socketUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      console.log('Connected to new order notification WebSocket');
    };

    socket.onmessage = (event: MessageEvent): void => {
      const dataRaw = event.data;
      try {
        const parsed =
          typeof dataRaw === 'string' ? JSON.parse(dataRaw) : dataRaw;

        if (parsed && parsed.type === 'order_created') {
          console.log('New order created:', parsed);

          const orderData = parsed as NewOrderMessage;
          const title = t('New order created');
          const message = `${orderData.order_code}${
            orderData.sender_name ? ` from ${orderData.sender_name}` : ''
          }${orderData.recipient_name ? ` to ${orderData.recipient_name}` : ''}`;

          // Use callback if provided, otherwise use default ToastTopHelper
          if (onNotification) {
            onNotification({ title, message, orderData });
          } else {
            // Fallback to simple console log if no notification system available
            console.info(`${title}: ${message}`);
          }
        }
      } catch (error) {
        console.error('Error parsing new order notification:', error);
      }
    };

    socket.onclose = () => {
      setIsConnected(false);
      socketRef.current = null;
      console.log('Disconnected from new order notification WebSocket');
    };

    socket.onerror = (error) => {
      setIsConnected(false);
      console.error('New order notification WebSocket error:', error);
    };

    return () => {
      try {
        if (socketRef.current) {
          socketRef.current.close();
          socketRef.current = null;
        } else {
          socket.close();
        }
        console.log('Closed new order notification WebSocket');
      } catch (error) {
        console.error('Error closing new order notification WebSocket:', error);
      }
    };
  }, [socketUrl]);

  return { isConnected };
};
