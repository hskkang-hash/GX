import React, { CSSProperties, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { BsChevronLeft, BsChevronRight } from 'react-icons/bs';

import { AbnormalSignMessage } from '../hooks/useSurveillanceDashboard';
import { ANIMATION, COLORS, PAGE_SIZE } from './constants';
import { ThemeColors } from './utils/getThemeColors';

// ============================================================================
// NotificationItem Component
// ============================================================================
interface NotificationItemProps {
  message: AbnormalSignMessage;
  index: number;
  themeColors: ThemeColors;
  onNotificationClick?: (message: AbnormalSignMessage) => void;
}

export const NotificationItem: React.FC<NotificationItemProps> = ({
  message,
  index,
  themeColors,
  onNotificationClick,
}) => {
  const { t } = useTranslation();

  /**
   * Extract detect_name from message and translate it
   * Message always comes in English format: "Detected {detect_name}."
   * where detect_name can be:
   * - Single word: "fire", "smoke", "person"
   * - Multiple words: "traffic light", "fire hydrant"
   * - Slash-separated: "fire/smoke" (split and translate each part)
   */
  const translatedMessage = useMemo(() => {
    const originalMessage = message.message;
    if (!originalMessage) return originalMessage;

    // Extract detect_name from "Detected {detect_name}." format
    const englishPattern = /^Detected\s+(.+?)\.$/i;
    const match = originalMessage.match(englishPattern);

    if (match) {
      const detectNameKey = match[1].trim();

      // Handle slash-separated values like "fire/smoke"
      // Split by "/" and translate each part, then join with "/"
      if (detectNameKey.includes('/')) {
        const parts = detectNameKey
          .split('/')
          .map((part: string) => part.trim());
        const translatedParts = parts.map((part: string) => {
          const translated = t(
            `SurveillanceDashboard.DetectionLabels.${part}`,
            {
              defaultValue: part,
            },
          );
          return translated;
        });
        const translatedDetectName = translatedParts.join('/');

        // Format the final message using the template
        return t('SurveillanceDashboard.Detected {detect_name}.', {
          detect_name: translatedDetectName,
        });
      }

      // Translate single or multi-word detect_name using DetectionLabels
      // Fallback to original detect_name if translation not found
      const translatedDetectName = t(
        `SurveillanceDashboard.DetectionLabels.${detectNameKey}`,
        {
          defaultValue: detectNameKey,
        },
      );

      // Format the final message using the template
      return t('SurveillanceDashboard.Detected {detect_name}.', {
        detect_name: translatedDetectName,
      });
    }

    // If pattern doesn't match, return original message
    return originalMessage;
  }, [message.message, t]);

  const handleClick = () => {
    // Only trigger if notification has detected_image_path (has a marker on map)
    if (message.detected_image_path && onNotificationClick) {
      onNotificationClick(message);
    }
  };

  const containerStyle: CSSProperties = {
    display: 'flex',
    gap: '0.75rem',
    padding: '1rem',
    borderRadius: '0.75rem',
    backgroundColor: themeColors.background,
    justifyContent: 'space-between',
    alignItems: 'center',
    position: 'relative',
    cursor: message.detected_image_path ? 'pointer' : 'default',
    transition: 'background-color 0.2s ease',
  };

  const handleMouseEnter = (e: React.MouseEvent<HTMLDivElement>) => {
    if (message.detected_image_path) {
      e.currentTarget.style.backgroundColor = themeColors.backgroundAlt;
    }
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.backgroundColor = themeColors.background;
  };

  const contentStyle: CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '0.25rem',
  };

  const messageTextStyle: CSSProperties = {
    fontSize: '1rem',
    color: themeColors.text,
    fontWeight: 500,
  };

  const timeStyle: CSSProperties = {
    fontSize: '0.8rem',
    color: themeColors.textSecondary,
    flexShrink: 0,
  };

  const imageContainerStyle: CSSProperties = {
    backgroundColor: themeColors.backgroundAlt,
    borderRadius: '0.5rem',
    overflow: 'hidden',
    border: `1px solid ${themeColors.border}`,
    // width: '4rem',
    // height: '4rem',
    flexShrink: 0,
  };

  return (
    <div
      style={containerStyle}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div style={contentStyle}>
        <div style={messageTextStyle}>
          {index + 1}. {translatedMessage}
        </div>
        <div style={timeStyle}>{message.relative_time}</div>
      </div>
      {message.detected_image_path && (
        <div style={imageContainerStyle}>
          <img
            src={message.detected_image_path}
            alt="Detection"
            style={{
              width: '5rem',
              height: 'auto',
              objectFit: 'cover',
              display: 'block',
            }}
            onError={(e) => {
              // Fallback if image fails to load
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        </div>
      )}
    </div>
  );
};

// ============================================================================
// EmptyState Component
// ============================================================================
interface EmptyStateProps {
  message: string;
  themeColors: ThemeColors;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  message,
  themeColors,
}) => {
  const style: CSSProperties = {
    textAlign: 'center',
    color: themeColors.textSecondary,
    padding: '1.25rem',
  };

  return <div style={style}>{message}</div>;
};

// ============================================================================
// LoadingSkeleton Component
// ============================================================================
interface LoadingSkeletonProps {
  themeColors: ThemeColors;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  themeColors,
}) => {
  const containerStyle: CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  };

  const itemStyle: CSSProperties = {
    padding: '1rem',
    borderRadius: '0.75rem',
    backgroundColor: themeColors.background,
  };

  const headerStyle: CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '0.5rem',
  };

  const skeletonBarStyle = (width: string): CSSProperties => ({
    width,
    height: '1rem',
    backgroundColor: themeColors.skeletonPrimary,
    borderRadius: '0.25rem',
  });

  const skeletonSubtitleStyle: CSSProperties = {
    width: '40%',
    height: '0.75rem',
    backgroundColor: themeColors.skeletonSecondary,
    borderRadius: '0.25rem',
  };

  return (
    <div style={containerStyle}>
      {Array.from({ length: PAGE_SIZE }).map((_, index) => (
        <div
          key={index}
          style={itemStyle}
        >
          <div style={headerStyle}>
            <div style={skeletonBarStyle('60%')} />
            <div style={skeletonBarStyle('20%')} />
          </div>
          <div style={skeletonSubtitleStyle} />
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// ConnectionIndicator Component
// ============================================================================
interface ConnectionIndicatorProps {
  isConnected: boolean;
}

export const ConnectionIndicator: React.FC<ConnectionIndicatorProps> = ({
  isConnected,
}) => {
  const color = isConnected ? COLORS.CONNECTED : COLORS.CONNECTING;

  const containerStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '0.3rem',
    fontSize: '0.75rem',
    color,
    marginLeft: 'auto',
  };

  const dotStyle: CSSProperties = {
    width: '0.5rem',
    height: '0.5rem',
    borderRadius: '50%',
    backgroundColor: color,
    animation: isConnected ? 'pulse 2s infinite' : 'none',
  };

  return (
    <span style={containerStyle}>
      <span style={dotStyle} />
      {isConnected ? 'Live' : 'Connecting...'}
    </span>
  );
};

// ============================================================================
// PaginationButton Component
// ============================================================================
interface PaginationButtonProps {
  onClick: () => void;
  disabled: boolean;
  icon: React.ReactNode;
  themeColors: ThemeColors;
}

export const PaginationButton: React.FC<PaginationButtonProps> = ({
  onClick,
  disabled,
  icon,
  themeColors,
}) => {
  const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (disabled) return;

    e.currentTarget.style.borderColor = 'var(--ga-primary)';
    const iconElement = e.currentTarget.querySelector('svg');
    if (iconElement) {
      const htmlIcon = iconElement as unknown as HTMLElement;
      htmlIcon.style.transform = `scale(${ANIMATION.SCALE_HOVER})`;
      htmlIcon.style.color = 'var(--ga-primary)';
    }
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.currentTarget.style.borderColor = themeColors.border;
    const iconElement = e.currentTarget.querySelector('svg');
    if (iconElement) {
      const htmlIcon = iconElement as unknown as HTMLElement;
      htmlIcon.style.transform = `scale(${ANIMATION.SCALE_DEFAULT})`;
      htmlIcon.style.color = themeColors.text;
    }
  };

  const buttonStyle: CSSProperties = {
    width: '2rem',
    height: '2rem',
    borderRadius: '50%',
    border: `1px solid ${themeColors.border}`,
    backgroundColor: themeColors.backgroundAlt,
    color: themeColors.text,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    fontSize: '0.875rem',
    transition: ANIMATION.BUTTON_TRANSITION,
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={buttonStyle}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {icon}
    </button>
  );
};

// ============================================================================
// PaginationControls Component
// ============================================================================
interface PaginationControlsProps {
  currentPage: number;
  totalPages: number;
  isLoadingMore: boolean;
  isRealtime: boolean;
  themeColors: ThemeColors;
  onPreviousPage: () => void;
  onNextPage: () => void;
}

export const PaginationControls: React.FC<PaginationControlsProps> = ({
  currentPage,
  totalPages,
  isLoadingMore,
  themeColors,
  onPreviousPage,
  onNextPage,
}) => {
  if (totalPages <= 1) return null;

  const iconStyle = { transition: ANIMATION.TRANSITION };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '0.5rem',
      }}
    >
      <PaginationButton
        onClick={onPreviousPage}
        disabled={currentPage === 1 || isLoadingMore}
        icon={
          <BsChevronLeft
            size={16}
            style={iconStyle}
          />
        }
        themeColors={themeColors}
      />
      <PaginationButton
        onClick={onNextPage}
        disabled={currentPage === totalPages || isLoadingMore}
        icon={
          <BsChevronRight
            size={16}
            style={iconStyle}
          />
        }
        themeColors={themeColors}
      />
    </div>
  );
};

// ============================================================================
// NotificationsHeader Component
// ============================================================================
interface NotificationsHeaderProps {
  title: string;
  isRealtime: boolean;
  isWebSocketConnected: boolean;
  currentPage: number;
  totalPages: number;
  isLoadingMore: boolean;
  themeColors: ThemeColors;
  onPreviousPage: () => void;
  onNextPage: () => void;
}

export const NotificationsHeader: React.FC<NotificationsHeaderProps> = ({
  title,
  isRealtime,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  isWebSocketConnected,
  currentPage,
  totalPages,
  isLoadingMore,
  themeColors,
  onPreviousPage,
  onNextPage,
}) => {
  const containerStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '1rem',
    flexShrink: 0,
  };

  const titleStyle: CSSProperties = {
    margin: 0,
    fontSize: '1.25rem',
    color: themeColors.text,
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  };

  return (
    <div style={containerStyle}>
      <h3 style={titleStyle}>{title}</h3>

      <PaginationControls
        currentPage={currentPage}
        totalPages={totalPages}
        isLoadingMore={isLoadingMore}
        isRealtime={isRealtime}
        themeColors={themeColors}
        onPreviousPage={onPreviousPage}
        onNextPage={onNextPage}
      />
    </div>
  );
};

// ============================================================================
// NotificationsContent Component
// ============================================================================
interface NotificationsContentProps {
  messages: AbnormalSignMessage[];
  paginatedMessages: AbnormalSignMessage[];
  startIndex: number;
  isRealtime: boolean;
  isLoadingMore: boolean;
  emptyMessage: string;
  themeColors: ThemeColors;
  onNotificationClick?: (message: AbnormalSignMessage) => void;
}

export const NotificationsContent: React.FC<NotificationsContentProps> = ({
  messages,
  paginatedMessages,
  startIndex,
  isRealtime,
  isLoadingMore,
  emptyMessage,
  themeColors,
  onNotificationClick,
}) => {
  const containerStyle: CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  };

  // Show skeleton when paginating in completed mode
  if (!isRealtime && isLoadingMore) {
    return <LoadingSkeleton themeColors={themeColors} />;
  }

  // Show empty state
  if (!messages || messages.length === 0) {
    return (
      <EmptyState
        message={emptyMessage}
        themeColors={themeColors}
      />
    );
  }

  // Show notifications
  return (
    <div style={containerStyle}>
      {paginatedMessages.map((message, paginatedIndex) => {
        const actualIndex = startIndex + paginatedIndex;
        return (
          <NotificationItem
            key={message.id || actualIndex}
            message={message}
            index={actualIndex}
            themeColors={themeColors}
            onNotificationClick={onNotificationClick}
          />
        );
      })}
    </div>
  );
};
