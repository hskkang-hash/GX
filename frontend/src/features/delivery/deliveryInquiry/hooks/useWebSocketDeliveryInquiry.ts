import { useEffect, useRef, useState } from 'react';

type IncomingMessage = {
  'status.name': string;
  'pickup_location.city_county_district': string;
  'recipient_address.city': string;
  modified_on: string;
  order_code: string;
  recipient_name: string;
};

export const useWebSocketDeliveryInquiry = ({
  socketUrl,
}: {
  socketUrl: string;
}): { isConnected: boolean; message: IncomingMessage | null } => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [message, setMessage] = useState<IncomingMessage | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect((): (() => void) => {
    if (!socketUrl) {
      setIsConnected(false);
      setMessage(null);
      return () => {};
    }

    const socket = new WebSocket(socketUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      console.log('connected in useWebSocketDeliveryInquiry');
    };

    socket.onmessage = (event: MessageEvent): void => {
      const dataRaw = event.data;
      try {
        const parsed =
          typeof dataRaw === 'string' ? JSON.parse(dataRaw) : dataRaw;

        if (parsed && parsed.type === 'order_status_changed') {
          console.log('message', parsed);
          setMessage(parsed as IncomingMessage);
        }
      } catch {
        setMessage(dataRaw as IncomingMessage);
      }
    };

    socket.onclose = () => {
      setIsConnected(false);
      socketRef.current = null;
      console.log('closed in useWebSocketDeliveryInquiry');
    };

    socket.onerror = () => {
      setIsConnected(false);
      console.log('error in useWebSocketDeliveryInquiry');
    };

    return () => {
      try {
        if (socketRef.current) {
          socketRef.current.close();
          socketRef.current = null;
          console.log('closed in useWebSocketDeliveryInquiry');
        } else {
          socket.close();
          console.log('closed in useWebSocketDeliveryInquiry');
        }
      } catch {
        // no-op
      }
    };
  }, [socketUrl]);

  return { isConnected, message };
};
