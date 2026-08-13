import dayjs from 'dayjs';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  Container,
  CustomBreadcrumb,
  CustomBtn,
  CustomModal,
  Main,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import { CustomRoutes } from '@/services/API';

import { ACTION_TYPE_BTN } from '../../../../../configs/Constant';
import { remToPx } from '../../../../../utils/utils';
import { useDateFormat, useTimezoneCode } from '../../../hooks/useDateFormat';
import { HandoverNoticeState } from '../../../types';
import { formatDate } from '../../../utils/dateFormat';
import { ItemCard, ItemCardRef } from './components/ItemCard';
import { useHandoverManagement } from './hooks/useHandoverManagement';

export const CreateHandoverPage = () => {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const { id } = useParams();
  const { getListNoticeHandoverAPI } = useHandoverManagement();
  const { state } = useLocation();
  const { date } = state;
  const headerPageRef = useRef<HTMLDivElement>(null);
  const { dateFormat } = useDateFormat();
  const { timezoneCode } = useTimezoneCode();
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(5)],
  });
  const [noticeList, setNoticeList] = useState<HandoverNoticeState[]>([]);
  const [showUnsavedModal, setShowUnsavedModal] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const itemCardRefs = useRef<Map<number, ItemCardRef>>(new Map());
  const [dirtyItems, setDirtyItems] = useState<Set<number>>(new Set());

  const handleGetListNoticeHandover = useCallback(
    async (temp_id?: number) => {
      const { success, data, message } = await getListNoticeHandoverAPI(
        Number(id),
      );
      if (success) {
        setNoticeList((prev) => {
          // Giữ lại tất cả các item temp (id < 0) trừ item có temp_id được truyền vào
          const tempItems = prev.filter(
            (item: HandoverNoticeState) =>
              item.id < 0 && (!temp_id || item.id !== temp_id),
          );
          // Lấy các item thật từ API (id >= 0)
          const realItems = data.filter(
            (item: HandoverNoticeState) => item.id >= 0,
          );
          // Kết hợp temp items và real items
          return [...tempItems, ...realItems];
        });
      } else {
        setNoticeList([]);
        ToastTopHelper.error(message);
      }
    },
    [getListNoticeHandoverAPI, id],
  );

  useEffect(() => {
    if (id) {
      handleGetListNoticeHandover();
    }
  }, [id]);

  const handleAddMoreContent = useCallback(() => {
    setNoticeList((prev) => [
      {
        id: -Date.now() - Math.floor(Math.random() * 1000),
        content: '',
        is_notice: false,
        handover_doc_id: Number(id),
        created_time: '',
        updated_time: '',
        creator_full_name: '',
        editor: '',
        editor_full_name: '',
        is_edit: false,
      },
      ...prev,
    ]);
  }, [id]);

  const handleDirtyChange = useCallback((itemId: number, isDirty: boolean) => {
    setDirtyItems((prev) => {
      const newSet = new Set(prev);
      if (isDirty) {
        newSet.add(itemId);
      } else {
        newSet.delete(itemId);
      }
      return newSet;
    });
  }, []);

  const hasUnsavedChanges = dirtyItems.size > 0;

  const handleBackClick = useCallback(() => {
    if (hasUnsavedChanges) {
      setShowUnsavedModal(true);
    } else {
      navigate(CustomRoutes.handover.path);
    }
  }, [hasUnsavedChanges, navigate]);

  const handleSaveAndBack = useCallback(async () => {
    setIsSaving(true);
    try {
      const savePromises = Array.from(dirtyItems).map((itemId) => {
        const ref = itemCardRefs.current.get(itemId);
        return ref?.handleSave() ?? Promise.resolve(true);
      });

      const results = await Promise.all(savePromises);
      const allSuccess = results.every((result) => result === true);

      if (allSuccess) {
        setShowUnsavedModal(false);
        navigate(CustomRoutes.handover.path);
      }
    } catch (error) {
      console.error('Error saving items:', error);
    } finally {
      setIsSaving(false);
    }
  }, [dirtyItems, navigate]);

  const handleNotSaveAndBack = useCallback(() => {
    setShowUnsavedModal(false);
    navigate(CustomRoutes.handover.path);
  }, [navigate]);

  const handleCancelModal = useCallback(() => {
    setShowUnsavedModal(false);
  }, []);

  const handleRemoveItem = useCallback((itemId: number) => {
    setNoticeList((prev) => prev.filter((item) => item.id !== itemId));
    itemCardRefs.current.delete(itemId);
    setDirtyItems((prev) => {
      const newSet = new Set(prev);
      newSet.delete(itemId);
      return newSet;
    });
  }, []);

  return (
    <Container>
      <CustomBreadcrumb
        ref={headerPageRef}
        items={[
          { url: '/handover' },
          {
            text:
              i18n.language === 'en'
                ? `Day shift log for ${formatDate(date, dateFormat, i18n.language, timezoneCode)}`
                : i18n.language === 'ko'
                  ? `${formatDate(date, dateFormat, i18n.language, timezoneCode)} 일간 로그`
                  : `${formatDate(date, dateFormat, i18n.language, timezoneCode)} ลงรายการวันนับถือ`,
          },
        ]}
        buttons={[
          <CustomBtn
            key="back-btn"
            type="button"
            variant="outline"
            color="secondary"
            label={t('handover.Back to handover')}
            onClick={handleBackClick}
          />,
          <CustomBtn
            actionType={ACTION_TYPE_BTN.UPDATE}
            color="primary"
            type="button"
            icon={<i className="bi bi-plus-lg"></i>}
            label={t('handover.Add More Content')}
            onClick={handleAddMoreContent}
          />,
        ]}
      />
      <Main>
        <div
          className="d-flex flex-column gap-3"
          style={{
            height: `${spaceTableHeight}px`,
            overflowY: 'auto',
            overflowX: 'hidden',
          }}
        >
          {noticeList.map((item) => (
            <ItemCard
              key={item.id}
              ref={(ref) => {
                if (ref) {
                  itemCardRefs.current.set(item.id, ref);
                } else {
                  itemCardRefs.current.delete(item.id);
                }
              }}
              item={item}
              handleGetListNoticeHandover={handleGetListNoticeHandover}
              onDirtyChange={(isDirty) => handleDirtyChange(item.id, isDirty)}
              onRemoveItem={handleRemoveItem}
            />
          ))}
        </div>
      </Main>
      {showUnsavedModal && (
        <CustomModal
          title={t('handover.Back to Handover')}
          show={showUnsavedModal}
          onHide={handleCancelModal}
        >
          <div style={{ width: '25rem' }}>
            {t(
              'handover.Some of handovers have not been saved. Do you want to save them before moving to the list?',
            )}
          </div>
          <div className="d-flex gap-3 my-3">
            <CustomBtn
              key="save-and-back-btn"
              type="button"
              color="primary"
              size="lg"
              label={t('handover.Save and Back')}
              onClick={handleSaveAndBack}
              disabled={isSaving}
              loading={isSaving}
            />
            <CustomBtn
              key="not-save-and-back-btn"
              type="button"
              variant="outline"
              color="primary"
              size="lg"
              label={t('handover.Not Save and Back')}
              onClick={handleNotSaveAndBack}
              disabled={isSaving}
            />
            <CustomBtn
              key="cancel-btn"
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              label={t('handover.Cancel')}
              onClick={handleCancelModal}
              disabled={isSaving}
            />
          </div>
        </CustomModal>
      )}
    </Container>
  );
};
