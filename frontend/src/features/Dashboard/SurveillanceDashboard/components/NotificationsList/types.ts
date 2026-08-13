import { AbnormalSignMessage } from '../../hooks/useSurveillanceDashboard';

export interface NotificationsListProps {
  messages: AbnormalSignMessage[];
  isLoading?: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  isWebSocketConnected?: boolean;
  notificationStatus?: 'realtime' | 'completed';
  currentApiPage?: number;
  totalApiPages?: number;
  onPageChange?: (page: number) => void;
  /** Callback when a notification item is clicked */
  onNotificationClick?: (message: AbnormalSignMessage) => void;
}

export interface PaginationState {
  currentPage: number;
  totalPages: number;
  startIndex: number;
  endIndex: number;
  isRealtime: boolean;
}

