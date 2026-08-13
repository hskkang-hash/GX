import { notification } from 'antd';
import React, { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { FaTruck, FaBuilding, FaBell } from 'react-icons/fa';
import { IoWarning, IoInformationCircle } from 'react-icons/io5';

import { usePartnerCallbackWebSocket } from '@/hooks/usePartnerCallbackWebSocket';

// Helper function để format notification content
const getNotificationContent = (message: any, t: any) => {
  const timeStr = new Date().toLocaleTimeString();

  switch (message.type) {
    case 'delivery_status_callback':
      return {
        title: '🚚 Delivery Status Update',
        description: (
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            <p
              style={{
                fontSize: '0.95rem',
                marginBottom: '0.5rem',
                fontWeight: 500,
              }}
            >
              Partner callback received ({timeStr})
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#1890ff' }}>
                Item ID:{' '}
              </span>
              <span style={{ fontWeight: 600 }}>{message.data?.itemOrgId}</span>
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#1890ff' }}>
                Status:{' '}
              </span>
              <span>{message.data?.deliveryStatus}</span>
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#1890ff' }}>
                Updated:{' '}
              </span>
              <span>{message.data?.updateTime || message.timestamp}</span>
            </p>
            {message.partner_info?.serviceKey_prefix && (
              <p
                style={{ marginBottom: 0, fontSize: '0.85rem', color: '#666' }}
              >
                Service: {message.partner_info.serviceKey_prefix}
              </p>
            )}
          </div>
        ),
        style: { backgroundColor: '#e6f7ff', borderColor: '#91d5ff' },
      };

    case 'drone_base_station_callback':
      return {
        title: '🏢 Base Station Update',
        description: (
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            <p
              style={{
                fontSize: '0.95rem',
                marginBottom: '0.5rem',
                fontWeight: 500,
              }}
            >
              Station status callback received ({timeStr})
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#52c41a' }}>
                Station:{' '}
              </span>
              <span style={{ fontWeight: 600 }}>
                {message.data?.startDeliveryPoint}
              </span>
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#52c41a' }}>
                Status:{' '}
              </span>
              <span>{message.data?.status}</span>
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#52c41a' }}>
                Message:{' '}
              </span>
              <span>{message.data?.message}</span>
            </p>
            {message.partner_info?.serviceKey_prefix && (
              <p
                style={{ marginBottom: 0, fontSize: '0.85rem', color: '#666' }}
              >
                Service: {message.partner_info.serviceKey_prefix}
              </p>
            )}
          </div>
        ),
        style: { backgroundColor: '#f6ffed', borderColor: '#b7eb8f' },
      };

    case 'drone_user_notice_callback':
      return {
        title: '📢 User Notice',
        description: (
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            <p
              style={{
                fontSize: '0.95rem',
                marginBottom: '0.5rem',
                fontWeight: 500,
              }}
            >
              User notice callback received ({timeStr})
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#faad14' }}>
                Area Code:{' '}
              </span>
              <span style={{ fontWeight: 600 }}>{message.data?.BCode}</span>
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#faad14' }}>
                Notice:{' '}
              </span>
              <span>{message.data?.IsNotice ? 'Active' : 'Inactive'}</span>
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#faad14' }}>
                Content:{' '}
              </span>
              <span>{message.data?.Html1}</span>
            </p>
            {message.data?.Html2 && (
              <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
                <span style={{ fontWeight: 600, color: '#faad14' }}>
                  Additional:{' '}
                </span>
                <span>{message.data.Html2}</span>
              </p>
            )}
            {message.partner_info?.serviceKey_prefix && (
              <p
                style={{ marginBottom: 0, fontSize: '0.85rem', color: '#666' }}
              >
                Service: {message.partner_info.serviceKey_prefix}
              </p>
            )}
          </div>
        ),
        style: { backgroundColor: '#fffbe6', borderColor: '#ffe58f' },
      };

    case 'partner_callback_error':
      return {
        title: '❌ Partner Callback Error',
        description: (
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            <p
              style={{
                fontSize: '0.95rem',
                marginBottom: '0.5rem',
                fontWeight: 500,
              }}
            >
              Error occurred ({timeStr})
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#ff4d4f' }}>Error: </span>
              <span>{message.error || message.message || 'Unknown error'}</span>
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600, color: '#ff4d4f' }}>Type: </span>
              <span>{message.callback_type || 'Unknown'}</span>
            </p>
          </div>
        ),
        style: { backgroundColor: '#fff2f0', borderColor: '#ffccc7' },
      };

    default:
      return {
        title: '📝 Partner Notification',
        description: (
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            <p
              style={{
                fontSize: '0.95rem',
                marginBottom: '0.5rem',
                fontWeight: 500,
              }}
            >
              Partner notification received ({timeStr})
            </p>
            <p style={{ marginBottom: '0.25rem', fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600 }}>Type: </span>
              <span>{message.type}</span>
            </p>
            <p style={{ marginBottom: 0, fontSize: '0.95rem' }}>
              <span style={{ fontWeight: 600 }}>Message: </span>
              <span>{message.message || 'No details'}</span>
            </p>
          </div>
        ),
        style: { backgroundColor: '#f5f5f5', borderColor: '#d9d9d9' },
      };
  }
};

const PartnerCallbackNotificationPopup: React.FC = () => {
  const { t } = useTranslation();
  const [api, contextHolder] = notification.useNotification();
  const clearMessageTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const { isConnected, message, clearMessage } = usePartnerCallbackWebSocket({
    socketUrl: `${import.meta.env.VITE_STREAMING_WS}/ws/partner-callbacks/`,
  });

  useEffect(() => {
    return () => {
      if (clearMessageTimeoutRef.current) {
        clearTimeout(clearMessageTimeoutRef.current);
        clearMessageTimeoutRef.current = null;
      }
    };
  }, []);

  // Auto-show notification when new message arrives
  useEffect(() => {
    console.log('🎯 [DEBUG] useEffect triggered with message:', message);

    if (message && message.type !== 'connected') {
      console.log(
        '🎯 [DEBUG] ✅ Showing Antd notification for message type:',
        message.type,
      );

      const notificationContent = getNotificationContent(message, t);

      api.open({
        message: notificationContent.title,
        description: notificationContent.description,
        duration: 6, // Auto close after 6 seconds
        placement: 'topRight',
        style: {
          width: 400,
          padding: '1.5rem',
          borderRadius: '0.8rem',
          ...notificationContent.style,
        },
        className: 'partner-callback-notification',
      });

      // Clear previous timeout if exists
      if (clearMessageTimeoutRef.current) {
        clearTimeout(clearMessageTimeoutRef.current);
      }

      // Clear message after showing notification
      clearMessageTimeoutRef.current = setTimeout(() => {
        clearMessage();
        clearMessageTimeoutRef.current = null;
      }, 100);
    }
  }, [message, api, t, clearMessage]);

  return <>{contextHolder}</>;
};

export default PartnerCallbackNotificationPopup;
