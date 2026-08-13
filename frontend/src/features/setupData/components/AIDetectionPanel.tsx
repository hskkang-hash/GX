import {
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { List, Typography, Empty } from 'antd';
import dayjs from 'dayjs';
import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';
import { useConvertDate } from '../../Dashboard/utils/formatDateTime';

const { Title, Text } = Typography;

// AI Detection Notification types
export type NotificationSeverity = 'error' | 'warning' | 'success' | 'info';

export type NotificationType =
  | 'communication_error'
  | 'mission_completed'
  | 'intruder_detection'
  | 'suspicious_movement'
  | 'battery_low'
  | 'gps_lost';

// Detection data from backend
export interface Detection {
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  confidence: number;
  color: string;
  class_id: number;
}

export interface DetectionMessage {
  timestamp: number;
  datetime: string;
  detections: Detection[];
  detection_count: number;
}

export interface AIDetectionNotification {
  id: string;
  drone_id: string;
  drone_name?: string;
  type: NotificationType;
  severity: NotificationSeverity;
  title: string;
  message: string;
  timestamp: string;
  zone?: string;
  detections?: Detection[];
  detection_count?: number;
  metadata?: {
    confidence?: number;
    detection_type?: string;
    image_url?: string;
    [key: string]: any;
  };
}

interface AIDetectionPanelProps {
  droneIds?: string[];
  aiStreamUrl?: string;
  maxNotifications?: number;
  title?: string;
  showHeader?: boolean;
}

/**
 * AI Detection Panel Component
 * Handles WebSocket connection to AI stream and displays AI detection notifications
 * WebSocket URL: ws://{ai_stream_url}/ws/{drone_uid}
 * This component is part of guardianx and handles AI-specific notifications
 */
const AIDetectionPanel: React.FC<AIDetectionPanelProps> = ({
  droneIds = [],
  aiStreamUrl = 'wss://media-ai-svc.gaion.dev',
  maxNotifications = 50,
  title,
  showHeader = true,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [notifications, setNotifications] = useState<AIDetectionNotification[]>(
    [],
  );
  const { timeZoneFormat } = useConvertDate();
  // Connect to AI detection WebSocket for each drone
  useEffect(() => {
    if (!aiStreamUrl || droneIds.length === 0) {
      return;
    }

    const newConnections = new Map<string, WebSocket>();

    console.log(`🚀 Initializing AI detection WebSocket connections...`);
    console.log(`   AI Stream URL: ${aiStreamUrl}`);
    console.log(`   Drone IDs: ${droneIds.join(', ')}`);

    droneIds.forEach((droneId) => {
      const wsUrl = `${aiStreamUrl}/ws/${droneId}`;

      try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => { };

        ws.onmessage = (event) => {
          console.log(`Received message for ${droneId}:`, event.data);

          try {
            const detectionData: DetectionMessage = JSON.parse(event.data);
            console.log(`📦 Parsed detection data:`, {
              timestamp: detectionData.timestamp,
              datetime: detectionData.datetime,
              detectionCount: detectionData.detection_count,
              detections: detectionData.detections,
            });

            // Check if there are detections
            if (
              detectionData.detections &&
              detectionData.detections.length > 0
            ) {
              // Create notifications for each detection
              const newNotifications: AIDetectionNotification[] =
                detectionData.detections.map((detection, index) => {
                  // Determine severity based on confidence
                  let severity: NotificationSeverity = 'info';
                  if (detection.confidence >= 0.8) {
                    severity = 'error';
                  } else if (detection.confidence >= 0.6) {
                    severity = 'warning';
                  }

                  // Create simple notification: {drone_id} - {label} detected
                  const notification: AIDetectionNotification = {
                    id: `${droneId}_${detectionData.timestamp}_${index}`,
                    drone_id: droneId,
                    type: 'intruder_detection',
                    severity: severity,
                    title: `${droneId} - ${detection.label} detected`,
                    message: `${droneId} - ${detection.label} detected`,
                    timestamp: detectionData.datetime,
                    metadata: {
                      confidence: detection.confidence,
                    },
                  };

                  return notification;
                });

              // Update notifications state
              setNotifications((prev) => {
                const updated = [...newNotifications, ...prev];
                return updated.slice(0, maxNotifications);
              });
            } else {
              console.log(`No detections in this message`);
            }
          } catch (error) {
            console.error(
              `Error parsing AI detection message for ${droneId}:`,
              error,
            );
            console.error(`   Raw data:`, event.data);
          }
        };

        ws.onerror = (error) => {
          console.error(`AI detection WebSocket error for ${droneId}:`, error);
        };

        ws.onclose = (event) => {
          // Log common close codes
          const closeCodeMeanings: Record<number, string> = {
            1000: 'Normal Closure',
            1001: 'Going Away',
            1002: 'Protocol Error',
            1003: 'Unsupported Data',
            1006: 'Abnormal Closure (no close frame)',
            1007: 'Invalid Frame Payload Data',
            1008: 'Policy Violation',
            1009: 'Message Too Big',
            1011: 'Internal Server Error',
          };

          if (closeCodeMeanings[event.code]) {
            console.log(`   Meaning: ${closeCodeMeanings[event.code]}`);
          }
        };

        newConnections.set(droneId, ws);
      } catch (error) {
        console.error(
          `❌ Failed to create WebSocket connection for ${droneId}:`,
          error,
        );
      }
    });

    // Cleanup on unmount
    return () => {
      newConnections.forEach((ws, droneId) => {
        console.log(`🔌 Disconnecting from AI detection stream for ${droneId}`);
        ws.close();
      });
    };
  }, [droneIds, aiStreamUrl, maxNotifications]);

  // All notifications are already AI detections (no need to filter)
  const aiDetections = useMemo(() => notifications, [notifications]);

  // Format timestamp
  const formatTime = useCallback(
    (timestamp: string) => {
      const now = dayjs().tz(timeZoneFormat);
      const notifTime = dayjs.utc(timestamp).tz(timeZoneFormat);
      const diffMs = now.diff(notifTime);
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 1) return t("Just now");
      if (diffMins < 60) return `${diffMins} ${t("minutes ago")}`;
      if (diffMins < 1440)
        return `${Math.floor(diffMins / 60)} ${t("hours ago")}`;
      return `${Math.floor(diffMins / 1440)} ${t("days ago")}`;
    },
    [t, timeZoneFormat]
  );


  // Get icon based on severity
  const getSeverityIcon = (severity: NotificationSeverity) => {
    switch (severity) {
      case 'error':
        return (
          <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: '18px' }} />
        );
      case 'warning':
        return (
          <WarningOutlined style={{ color: '#faad14', fontSize: '18px' }} />
        );
      case 'success':
        return (
          <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '18px' }} />
        );
      case 'info':
      default:
        return (
          <InfoCircleOutlined style={{ color: '#faad14', fontSize: '18px' }} />
        );
    }
  };

  // Render notification item
  const renderNotificationItem = (notification: AIDetectionNotification) => (
    <List.Item
      key={notification.id}
      style={{
        padding: '12px 16px',
        borderBottom:
          theme === 'dark' ? '1px solid #404040' : '1px solid #f0f0f0',
        backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
        cursor: 'pointer',
        borderRadius: '10px',
        marginBottom: '10px',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '0.25rem',
          width: '100%',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          {/* Icon */}
          <div style={{ flexShrink: 0, paddingTop: '2px' }}>
            {/* {getSeverityIcon(notification.severity)} */}
            <InfoCircleOutlined
              style={{ color: '#faad14', fontSize: '18px' }}
            />
          </div>
          {/* Time */}
          <Text
            type="secondary"
            style={{
              fontSize: '12px',
              display: 'block',
              color: theme === 'dark' ? '#ffffff' : '#000000',
            }}
          >
            {formatTime(notification.timestamp)}
          </Text>
        </div>

        {/* Content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text
            style={{
              fontSize: '13px',
              color: theme === 'dark' ? '#ffffff' : '#000000',
              display: 'block',
              marginTop: '4px',
              lineHeight: '1.4',
            }}
          >
            {notification.message}
          </Text>
        </div>
      </div>
    </List.Item>
  );

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: theme === 'dark' ? '#1F1F20' : '#fff',
        borderRadius: '10px',
        padding: '1rem',
      }}
    >
      {/* Header */}
      {showHeader && (
        <div style={{ marginBottom: '1rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              color: theme === 'dark' ? '#ffffff' : '#000000',
            }}
          >
            <Title
              level={5}
              style={{
                margin: 0,
                fontSize: '14px',
                fontWeight: 600,
                color: theme === 'dark' ? '#ffffff' : '#000000',
              }}
            >
              {title || t('AI Detections')}
            </Title>

            {/* Connection Status Indicator */}
            {/* <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              {Array.from(connectionStatus.entries()).map(
                ([droneId, status]) => {
                  const statusColors = {
                    connecting: '#faad14',
                    connected: '#52c41a',
                    disconnected: '#d9d9d9',
                    error: '#ff4d4f',
                  };
                  const statusLabels = {
                    connecting: '⟳',
                    connected: '●',
                    disconnected: '○',
                    error: '⚠',
                  };

                  return (
                    <div
                      key={droneId}
                      style={{
                        fontSize: '12px',
                        color: statusColors[status],
                        fontWeight: 'bold',
                      }}
                      title={`${droneId}: ${status}`}
                    >
                      {statusLabels[status]}
                    </div>
                  );
                },
              )}
            </div> */}
          </div>

          {/* Debug Info */}
          {/* {connectionStatus.size > 0 && (
            <Text
              type="secondary"
              style={{ fontSize: '10px', display: 'block', marginTop: '4px' }}
            >
              {Array.from(connectionStatus.entries())
                .map(([id, status]) => `${id.split('_').pop()}: ${status}`)
                .join(' | ')}
            </Text>
          )} */}
        </div>
      )}

      {/* Notification List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
        }}
        className="scrollbar-custom"
      >
        {aiDetections.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={t('No detections')}
            style={{
              marginTop: '40px',
            }}
            styles={{
              description: {
                color: theme === 'dark' ? '#ffffff' : '#000000',
              },
            }}
          />
        ) : (
          <List
            dataSource={aiDetections}
            renderItem={renderNotificationItem}
            split={false}
          />
        )}
      </div>
    </div>
  );
};

export default AIDetectionPanel;
