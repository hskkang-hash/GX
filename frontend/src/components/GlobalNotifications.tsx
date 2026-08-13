import { notification } from 'antd';
import { useTranslation } from 'react-i18next';

import { useNewOrderNotification } from '@/hooks/useNewOrderNotification';

import './GlobalNotifications.scss';

const GlobalNotifications = () => {
  const { t } = useTranslation();
  const [api, contextHolder] = notification.useNotification();
  const openNewOrderNotification = ({
    title,
    orderCode,
    senderName,
    recipientName,
    time,
  }: {
    title: string;
    orderCode: string;
    senderName?: string;
    recipientName?: string;
    time: string;
  }) => {
    // Use current theme colors directly in styles to ensure immediate theme response
    const backgroundColor = '#D6F8E2';
    const textColor = '#333';
    const timeColor = '#333';

    api.open({
      message: (
        <h5
          style={{
            marginBottom: '0.25rem',
            fontSize: '1.1rem',
            fontWeight: 600,
            color: '#0cba47',
          }}
        >
          {title}
        </h5>
      ),
      description: (
        <div
          style={{
            maxHeight: '200px',
            overflowY: 'auto',
            scrollbarWidth: 'thin',
            scrollbarColor: '#0cba47 #f0f0f0',
          }}
        >
          <p
            style={{
              fontSize: '0.95rem',
              marginBottom: '0.5rem',
              fontWeight: 500,
              color: timeColor,
            }}
          >
            {t('New order created')} ({time})
          </p>
          {orderCode && (
            <p
              style={{
                marginBottom: '0.25rem',
                fontSize: '0.95rem',
              }}
            >
              <span style={{ fontWeight: 600, color: '#0cba47' }}>
                {t('Order ID: ')}
              </span>
              <span style={{ color: textColor, fontWeight: 600 }}>
                {orderCode}
              </span>
            </p>
          )}
          {senderName && (
            <p
              style={{
                marginBottom: '0.25rem',
                fontSize: '0.95rem',
              }}
            >
              <span style={{ fontWeight: 600, color: '#0cba47' }}>
                {t('Sender: ')}
              </span>
              <span style={{ color: textColor }}>{senderName}</span>
            </p>
          )}
          {recipientName && (
            <p
              style={{
                marginBottom: 0,
                fontSize: '0.95rem',
              }}
            >
              <span style={{ fontWeight: 600, color: '#0cba47' }}>
                {t('Recipient: ')}
              </span>
              <span style={{ color: textColor }}>{recipientName}</span>
            </p>
          )}
        </div>
      ),
      duration: 4, // Auto close after 6 seconds
      className: 'new-order-notification',
      style: {
        width: 350,
        padding: '1.5rem',
        borderRadius: '0.8rem',
        backgroundColor,
      },
      placement: 'topRight',
    });
  };

  // Initialize global new order notifications
  useNewOrderNotification({
    socketUrl: `${import.meta.env.VITE_STREAMING_WS}/ws/orders/notifications/`,
    onNotification: ({ title, message: orderMessage, orderData }) => {
      console.log('🎯 orderData', orderData);
      openNewOrderNotification({
        title,
        orderCode: orderData?.order?.order_code,
        time: new Date().toLocaleTimeString(),
      });
    },
  });

  return <>{contextHolder}</>;
};

export default GlobalNotifications;
