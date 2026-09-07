import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import { Carousel } from 'antd';
import { ComponentRef, useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomModal,
  ToastTopHelper,
  useTheme,
} from 'rj-core';

import { useHandover } from '../hooks/useHandover';
import { NoticeManagementState } from '../types';
import { failureLine } from '@/features/session/apiFailure';

const CardItem = ({
  index,
  item,
  onComplete,
  onDelete,
}: {
  index: number;
  item: NoticeManagementState;
  onComplete: (id: number) => void;
  onDelete: (id: number) => void;
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();

  return (
    <div
      key={`card-item-${index}`}
      style={{
        height: '9rem',
        flex: '1 1 calc((100% - 2rem) / 3)',
        minWidth: 0,
        display: 'flex',
        backgroundColor: theme === 'dark' ? '#1f1f1f' : '#ffffff',
        borderRadius: '4px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      }}
    >
      {/* Orange vertical bar on the left */}
      <div
        style={{
          width: '4px',
          backgroundColor: '#ff6b35',
          flexShrink: 0,
        }}
      />
      {/* Main content area */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          padding: '1rem',
          gap: '0.75rem',
        }}
      >
        {/* Header section with user name and timestamp */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            style={{
              fontWeight: '600',
              fontSize: '1rem',
              color: theme === 'dark' ? '#ffffff' : '#333333',
            }}
          >
            {item.creator__full_name || 'Unknown'}
          </span>
          <span
            style={{
              color: '#9C9D9D',
              fontSize: '0.85rem',
            }}
          >
            •
          </span>
          <span
            style={{
              fontWeight: '400',
              fontSize: '0.85rem',
              color: '#9C9D9D',
            }}
          >
            {item.created_time || ''}
          </span>
        </div>
        {/* Content section */}
        <div
          className="notice-content-scrollable"
          style={{
            flex: 1,
            overflowY: 'auto',
            overflowX: 'hidden',
            color: theme === 'dark' ? '#e0e0e0' : '#333333',
            fontSize: '1rem',
            lineHeight: '1.5',
            height: '100%',
            overflowWrap: 'anywhere',
          }}
        >
          {item.content || ''}
        </div>
      </div>
      {/* Action buttons on the right */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          padding: '2rem',
          justifyContent: 'center',
        }}
      >
        <CustomBtn
          label={t('Complete')}
          variant={'outline'}
          style={{
            border: 'none',
            background: 'none',
            fontWeight: '600',
            fontSize: '1rem',
            color:
              theme === 'dark' ? 'var(--ga-primary-dark)' : 'var(--ga-primary)',
            padding: 0,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
          onClick={() => onComplete(item.id)}
        />
        <CustomBtn
          label={t('handover.Delete')}
          variant={'outline'}
          style={{
            border: 'none',
            background: 'none',
            fontWeight: '600',
            fontSize: '1rem',
            color: theme === 'dark' ? '#ffffff' : '#333333',
            padding: 0,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
          onClick={() => onDelete(item.id)}
        />
      </div>
    </div>
  );
};

export const NoticeSlider = ({
  ref,
  items,
  handleRefresh,
}: {
  ref: React.RefObject<HTMLDivElement | null>;
  items: NoticeManagementState[];
  handleRefresh: () => void;
}) => {
  const carouselRef = useRef<ComponentRef<typeof Carousel>>(null);
  const [theme] = useTheme();
  const { t } = useTranslation();
  const [showCompleteNotice, setShowCompleteNotice] = useState<{
    show: boolean;
    id: number | null;
  }>({
    show: false,
    id: null,
  });
  const [showDeleteNotice, setShowDeleteNotice] = useState<{
    show: boolean;
    id: number | null;
  }>({
    show: false,
    id: null,
  });

  const { completeNoticeAPI, deleteNoticeAPI } = useHandover();

  // Group items into chunks of 3
  const chunkArray = <T,>(array: T[], chunkSize: number): T[][] => {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize));
    }
    return chunks;
  };

  const handleComplete = useCallback(
    async (id: number | null) => {
      // ★ [SEC-11a ② · 2026-09-07 턴 J · 차선 C] **거절을 삼키지 않는다.**
      //   `try` 가 없던 자리다. 접두 승격이 켜지면 이 `await` 는 예외로 끝나고,
      //   전역 `unhandledrejection` 처리기는 이 저장소에 0건이다 — 즉 **조용히 멈춘다.**
      if (!id) return;
      try {
        const { success, message } = await completeNoticeAPI(id);
        if (success) {
          ToastTopHelper.success(message);
          handleRefresh();
          setShowCompleteNotice({ show: false, id: null });
        } else {
          ToastTopHelper.error(message || 'Failed to complete notice');
        }
      } catch (error) {
        ToastTopHelper.error(failureLine('NoticeSlider.complete', error));
      } finally {
        // 확인 상자를 **반드시 닫는다.** 열린 채로 남으면 사람이 같은 단추를 또 누른다.
        setShowCompleteNotice({ show: false, id: null });
      }
    },
    [completeNoticeAPI, handleRefresh],
  );

  const handleDelete = useCallback(
    async (id: number | null) => {
      // ★ [SEC-11a ② · 2026-09-07 턴 J · 차선 C] **거절을 삼키지 않는다.**
      //   `try` 가 없던 자리다. 접두 승격이 켜지면 이 `await` 는 예외로 끝나고,
      //   전역 `unhandledrejection` 처리기는 이 저장소에 0건이다 — 즉 **조용히 멈춘다.**
      if (!id) return;
      try {
        const { success, message } = await deleteNoticeAPI(id);
        if (success) {
          ToastTopHelper.success(message);
          handleRefresh();
          setShowDeleteNotice({ show: false, id: null });
        } else {
          ToastTopHelper.error(message || 'Failed to delete notice');
        }
      } catch (error) {
        ToastTopHelper.error(failureLine('NoticeSlider.delete', error));
      } finally {
        setShowDeleteNotice({ show: false, id: null });
      }
    },
    [deleteNoticeAPI, handleRefresh],
  );

  if (!items || items.length === 0) {
    return null;
  }

  const itemChunks = chunkArray(items, 3);

  const handlePrev = (): void => {
    carouselRef.current?.prev();
  };

  const handleNext = (): void => {
    carouselRef.current?.next();
  };

  return (
    <div
      ref={ref}
      style={{ position: 'relative' }}
    >
      <style>
        {`
          .notice-content-scrollable::-webkit-scrollbar {
            width: 8px;
          }
          .notice-content-scrollable::-webkit-scrollbar-track {
            background: ${theme === 'dark' ? '#2f2f2f' : '#f1f1f1'};
            border-radius: 4px;
          }
          .notice-content-scrollable::-webkit-scrollbar-thumb {
            background: ${theme === 'dark' ? '#666666' : '#888888'};
            border-radius: 4px;
          }
          .notice-content-scrollable::-webkit-scrollbar-thumb:hover {
            background: ${theme === 'dark' ? '#888888' : '#666666'};
          }
          .notice-content-scrollable {
            scrollbar-width: thin;
            scrollbar-color: ${theme === 'dark' ? '#666666 #2f2f2f' : '#888888 #f1f1f1'};
          }
        `}
      </style>
      <Carousel
        ref={carouselRef}
        autoplay
        autoplaySpeed={15000}
        pauseOnHover={true}
        arrows={false}
        dots={false}
      >
        {itemChunks.map((chunk, chunkIndex) => (
          <div key={`slide-${chunkIndex}`}>
            <div
              style={{
                display: 'flex',
                gap: '1rem',
                marginBottom: '0.5rem',
              }}
            >
              {chunk.map((item, itemIndex) => (
                <CardItem
                  key={`item-${item.id}`}
                  index={chunkIndex * 3 + itemIndex}
                  item={item}
                  onComplete={() =>
                    setShowCompleteNotice({ show: true, id: Number(item.id) })
                  }
                  onDelete={() =>
                    setShowDeleteNotice({ show: true, id: Number(item.id) })
                  }
                />
              ))}
              {/* Fill remaining slots if chunk has less than 3 items */}
              {chunk.length < 3 &&
                Array.from({ length: 3 - chunk.length }).map((_, fillIndex) => (
                  <div
                    key={`fill-${fillIndex}`}
                    style={{
                      height: '9rem',
                      flex: '1 1 calc((100% - 2rem) / 3)',
                      minWidth: 0,
                    }}
                  />
                ))}
            </div>
          </div>
        ))}
      </Carousel>
      {/* Custom arrow buttons - stacked vertically on the right */}
      <div
        style={{
          position: 'absolute',
          right: -10,
          top: '50%',
          transform: 'translateY(-50%)',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
        }}
      >
        <button
          onClick={handlePrev}
          style={{
            width: '2rem',
            height: '2rem',
            borderRadius: '50%',
            border: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E5E7EB'}`,
            backgroundColor: theme === 'dark' ? '#1f1f1f' : '#ffffff',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.3s ease',
            opacity: 0.8,
            padding: 0,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor =
              theme === 'dark' ? '#2f2f2f' : '#f5f5f5';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor =
              theme === 'dark' ? '#1f1f1f' : '#ffffff';
          }}
        >
          <LeftOutlined
            style={{
              fontSize: '1rem',
              color: theme === 'dark' ? '#ffffff' : '#333333',
            }}
          />
        </button>
        <button
          onClick={handleNext}
          style={{
            width: '2rem',
            height: '2rem',
            borderRadius: '50%',
            border: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E5E7EB'}`,
            backgroundColor: theme === 'dark' ? '#1f1f1f' : '#ffffff',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.3s ease',
            opacity: 0.8,
            padding: 0,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor =
              theme === 'dark' ? '#2f2f2f' : '#f5f5f5';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor =
              theme === 'dark' ? '#1f1f1f' : '#ffffff';
          }}
        >
          <RightOutlined
            style={{
              fontSize: '1rem',
              color: theme === 'dark' ? '#ffffff' : '#333333',
            }}
          />
        </button>
      </div>

      <CustomModal
        title={t('handover.Complete Notice')}
        show={showCompleteNotice.show}
        onHide={() => setShowCompleteNotice({ show: false, id: null })}
        id="complete-notice"
      >
        <div className="text">
          {t('handover.Would you like to treat this notice as completed?')}
        </div>
        <ActionBtn
          leftButtons={[
            <CustomBtn
              color="primary"
              size="lg"
              label={t('handover.Ok')}
              type="button"
              onClick={() => handleComplete(showCompleteNotice.id)}
              id="save-button"
            />,
          ]}
          rightButtons={[
            <CustomBtn
              variant="outline"
              color="secondary"
              size="lg"
              label={t('handover.Cancel')}
              id="close-button"
              type="button"
              onClick={() => setShowCompleteNotice({ show: false, id: null })}
            />,
          ]}
        />
      </CustomModal>

      <CustomModal
        title={t('handover.Delete Notice')}
        show={showDeleteNotice.show}
        onHide={() => setShowDeleteNotice({ show: false, id: null })}
        id="delete-notice"
      >
        <div className="text">
          {t('handover.Are you sure you want to delete this notice?')}
        </div>
        <ActionBtn
          leftButtons={[
            <CustomBtn
              variant="outline"
              color="primary"
              size="lg"
              label={t('handover.Delete')}
              type="button"
              onClick={() => handleDelete(showDeleteNotice.id)}
              id="save-button"
            />,
          ]}
          rightButtons={[
            <CustomBtn
              variant="outline"
              color="secondary"
              size="lg"
              label={t('handover.Cancel')}
              id="close-button"
              type="button"
              onClick={() => setShowDeleteNotice({ show: false, id: null })}
            />,
          ]}
        />
      </CustomModal>
    </div>
  );
};
