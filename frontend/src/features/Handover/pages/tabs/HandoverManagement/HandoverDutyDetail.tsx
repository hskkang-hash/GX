import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBreadcrumb,
  CustomBtn,
  CustomModal,
  Main,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import i18n from '../../../../../i18n';
import { CustomRoutes } from '../../../../../services/API';
import { remToPx } from '../../../../../utils/utils';
import CustomCollapse from '../../../../FlightLogAnalysis/components/CustomCollapse';
import { useDateFormat, useTimezoneCode } from '../../../hooks/useDateFormat';
import { HandoverDutyDetailGrouped } from '../../../types';
import { formatDate } from '../../../utils/dateFormat';
import { groupHandoverDutyDetail } from '../../../utils/groupHandoverDutyDetail';
import { ItemCard, ItemCardRef } from './components/ItemCard';
import { useHandoverManagement } from './hooks/useHandoverManagement';

export const HandoverDutyDetail = () => {
  const headerPageRef = useRef<HTMLDivElement>(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(5)],
  });
  const { ids } = useLocation().state;
  const navigate = useNavigate();
  const { getHandoverDutyDetailAPI } = useHandoverManagement();
  const [handoverDutyDetail, setHandoverDutyDetail] = useState<
    HandoverDutyDetailGrouped[]
  >([]);
  const itemCardRefs = useRef<Map<number, ItemCardRef>>(new Map());
  const [dirtyItems, setDirtyItems] = useState<Set<number>>(new Set());
  const [showUnsavedModal, setShowUnsavedModal] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [activeKeys, setActiveKeys] = useState<number[]>(
    Array.from({ length: ids?.length || 0 }, (_, index) => index + 1),
  );
  const [theme] = useTheme();
  const { t } = useTranslation();
  const { dateFormat } = useDateFormat();
  const { timezoneCode } = useTimezoneCode();

  useEffect(() => {
    if (ids) {
      handleGetHandoverDutyDetail();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids]);

  const handleGetHandoverDutyDetail = useCallback(async () => {
    const { success, message, data } = await getHandoverDutyDetailAPI(ids);
    if (success) {
      const formattedData = groupHandoverDutyDetail(data);
      console.log('formattedData', formattedData);
      setHandoverDutyDetail(formattedData);
    } else {
      ToastTopHelper.error(message);
    }
  }, [ids, getHandoverDutyDetailAPI]);

  const hasUnsavedChanges = dirtyItems.size > 0;

  const handleBackClick = useCallback(() => {
    if (hasUnsavedChanges) {
      setShowUnsavedModal(true);
    } else {
      navigate(CustomRoutes.handover.path);
    }
  }, [hasUnsavedChanges, navigate]);

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

  const handleCancelModal = useCallback(() => {
    setShowUnsavedModal(false);
  }, []);

  const convertItems = useMemo(() => {
    return handoverDutyDetail.map((group, index) => ({
      key: index + 1,
      label: (
        <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>
          {`${group.shift_name} log for ${formatDate(group.date, dateFormat, i18n.language, timezoneCode)}`}
        </div>
      ),
      children: (
        <div className="d-flex flex-column gap-3">
          {group.data.map((item) => (
            <ItemCard
              key={item.id}
              item={item}
              ref={(ref) => {
                if (ref) {
                  itemCardRefs.current.set(item.id, ref);
                } else {
                  itemCardRefs.current.delete(item.id);
                }
              }}
              onDirtyChange={(isDirty) => handleDirtyChange(item.id, isDirty)}
              handleGetListNoticeHandover={handleGetHandoverDutyDetail}
            />
          ))}
        </div>
      ),
    }));
  }, [
    handoverDutyDetail,
    handleGetHandoverDutyDetail,
    handleDirtyChange,
    dateFormat,
  ]);

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

  return (
    <Container>
      <CustomBreadcrumb
        ref={headerPageRef}
        items={[
          { url: CustomRoutes.handover.path },
          { text: t('handover.Handover Duty Detail') },
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
        ]}
      />
      <Main>
        <div
          style={{
            height: `${spaceTableHeight}px`,
            overflowY: 'auto',
            overflowX: 'hidden',
          }}
        >
          <CustomCollapse
            activeKey={activeKeys}
            setActiveKey={(key) => {
              setActiveKeys(
                key.map((k) => (typeof k === 'string' ? Number(k) : k)),
              );
            }}
            items={convertItems}
            showExpandAll={true}
            colorLight="#F2F2F2"
            colorDark="#2D2E30"
            theme={theme === 'dark' ? 'dark' : 'light'}
          />
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
