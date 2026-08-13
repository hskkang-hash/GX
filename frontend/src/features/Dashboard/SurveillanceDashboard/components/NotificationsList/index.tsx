import React, { useRef, CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import NotificationsSkeleton from '../NotificationsSkeleton';
import { NotificationsContent, NotificationsHeader } from './components';
import { useInfiniteScroll } from './hooks/useInfiniteScroll';
import { usePagination } from './hooks/usePagination';
import { NotificationsListProps } from './types';
import { getThemeColors } from './utils/getThemeColors';

const NotificationsList: React.FC<NotificationsListProps> = ({
  messages,
  isLoading = false,
  onLoadMore,
  hasMore = false,
  isLoadingMore = false,
  isWebSocketConnected = false,
  notificationStatus = 'completed',
  currentApiPage = 1,
  totalApiPages = 0,
  onPageChange,
  onNotificationClick,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const loadMoreTriggerRef = useRef<HTMLDivElement>(null);

  const themeColors = getThemeColors(theme);

  const { paginationState, goToPreviousPage, goToNextPage } = usePagination({
    notificationStatus,
    messagesLength: messages.length,
    currentApiPage,
    totalApiPages,
  });

  const { currentPage, totalPages, startIndex, endIndex, isRealtime } =
    paginationState;

  const paginatedMessages = isRealtime
    ? messages.slice(startIndex, endIndex)
    : messages;

  useInfiniteScroll({
    isRealtime,
    scrollContainerRef,
    loadMoreTriggerRef,
    onLoadMore,
    hasMore,
    isLoadingMore,
  });

  const handlePreviousPage = () => {
    if (isRealtime) {
      goToPreviousPage();
    } else {
      onPageChange?.(Math.max(1, currentPage - 1));
    }
  };

  const handleNextPage = () => {
    if (isRealtime) {
      goToNextPage();
    } else {
      onPageChange?.(Math.min(totalPages, currentPage + 1));
    }
  };

  if (isLoading) {
    return <NotificationsSkeleton />;
  }

  const containerStyle: CSSProperties = {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    minHeight: 0,
    overflow: 'hidden',
  };

  const scrollStyle: CSSProperties = {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  };

  return (
    <div style={containerStyle}>
      <NotificationsHeader
        title={t('SurveillanceDashboard.Notifications')}
        isRealtime={isRealtime}
        isWebSocketConnected={isWebSocketConnected}
        currentPage={currentPage}
        totalPages={totalPages}
        isLoadingMore={isLoadingMore}
        themeColors={themeColors}
        onPreviousPage={handlePreviousPage}
        onNextPage={handleNextPage}
      />

      <div
        ref={scrollContainerRef}
        style={scrollStyle}
      >
        <NotificationsContent
          messages={messages}
          paginatedMessages={paginatedMessages}
          startIndex={startIndex}
          isRealtime={isRealtime}
          isLoadingMore={isLoadingMore}
          emptyMessage={t('SurveillanceDashboard.No notifications')}
          themeColors={themeColors}
          onNotificationClick={onNotificationClick}
        />
      </div>
    </div>
  );
};

export default NotificationsList;
