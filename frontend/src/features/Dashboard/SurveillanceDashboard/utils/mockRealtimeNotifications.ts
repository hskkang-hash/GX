/**
 * Mock data generator for testing realtime notifications with accurate timestamps
 *
 * Usage:
 * ```typescript
 * const mockGenerator = createMockNotificationGenerator();
 *
 * // Push a message every 6 seconds
 * const interval = setInterval(() => {
 *   const newMessage = mockGenerator.generateNext();
 *   setNotifications(prev => [newMessage, ...prev]);
 * }, 6000);
 * ```
 */

import { AbnormalSignMessage } from '../hooks/useSurveillanceDashboard';

const DETECTION_TYPES = [
  'fire',
  'smoke',
  'person',
  'car',
  'truck',
  'traffic light',
  'fire hydrant',
  'stop sign',
] as const;

const MOCK_IMAGES = [
  'https://via.placeholder.com/150/FF6B6B/FFFFFF?text=Fire',
  'https://via.placeholder.com/150/4ECDC4/FFFFFF?text=Smoke',
  'https://via.placeholder.com/150/45B7D1/FFFFFF?text=Person',
  'https://via.placeholder.com/150/FFA07A/FFFFFF?text=Vehicle',
] as const;

export interface MockNotificationGenerator {
  generateNext: () => AbnormalSignMessage;
  reset: () => void;
}

/**
 * Creates a mock notification generator that produces messages with accurate timestamps
 */
export const createMockNotificationGenerator =
  (): MockNotificationGenerator => {
    let counter = 0;

    return {
      generateNext: (): AbnormalSignMessage => {
        counter++;
        const detectionType =
          DETECTION_TYPES[Math.floor(Math.random() * DETECTION_TYPES.length)];
        const mockImage =
          MOCK_IMAGES[Math.floor(Math.random() * MOCK_IMAGES.length)];

        // Generate realistic coordinates (e.g., Seoul area)
        const baseLat = 37.5665;
        const baseLng = 126.978;
        const latitude = baseLat + (Math.random() - 0.5) * 0.1;
        const longitude = baseLng + (Math.random() - 0.5) * 0.1;

        return {
          id: `mock-${Date.now()}-${counter}`,
          timestamp: new Date().toISOString(), // ISO format timestamp
          category: 'warning',
          message: `Detected ${detectionType}.`,
          icon_type: 'warning',
          // Leave relative_time undefined - will be calculated by updateRelativeTime
          detected_image_path: mockImage,
          drone_location: {
            drone_id: `DRONE_${(counter % 5) + 1}`,
            location: {
              latitude,
              longitude,
              altitude: 50 + Math.random() * 50,
            },
            timestamp: Date.now(),
            age_seconds: 0,
          },
          detection_count: Math.floor(Math.random() * 5) + 1,
        };
      },
      reset: () => {
        counter = 0;
      },
    };
  };

/**
 * Calculate relative time from ISO timestamp
 * Examples: "Just now", "5s ago", "2m ago", "1h ago"
 */
export const calculateRelativeTime = (isoTimestamp: string): string => {
  const now = Date.now();
  const timestamp = new Date(isoTimestamp).getTime();
  const diffSeconds = Math.floor((now - timestamp) / 1000);

  if (diffSeconds < 10) return 'Just now';
  if (diffSeconds < 60) return `${diffSeconds}s ago`;

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
};

/**
 * Updates relative_time field for all messages based on their timestamp
 */
export const updateRelativeTime = (
  messages: AbnormalSignMessage[],
): AbnormalSignMessage[] => {
  return messages.map((msg) => ({
    ...msg,
    relative_time: calculateRelativeTime(msg.timestamp),
  }));
};
