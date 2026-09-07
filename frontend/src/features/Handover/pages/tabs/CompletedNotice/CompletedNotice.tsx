import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomizableTable,
  CustomModal,
  Main,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import { formatIsProcessed } from '../../../../../utils/formatColumns';
import { remToPx } from '../../../../../utils/utils';
import { NoticeSlider } from '../../../components/NoticeSlider';
import { COLUMNS_COMPLETED_NOTICE } from '../../../dataExample';
import { useHandover } from '../../../hooks/useHandover';
import { CompletedNoticeState, NoticeManagementState } from '../../../types';
import EditNotice from '../NoticeManagement/EditNotice';
import { useCompletedNotice } from './hooks/useCompletedNotice';
import { failureLine } from '@/features/session/apiFailure';

export const CompletedNotice = ({
  headerPageRef,
  openOffcanvas,
  setOpenOffcanvas,
  sliderData,
  getSliderDataAPI,
  onObjSearchChange,
}: {
  headerPageRef: React.RefObject<HTMLElement | null>;
  openOffcanvas: boolean;
  setOpenOffcanvas: (boolean: boolean) => void;
  sliderData: NoticeManagementState[];
  getSliderDataAPI: () => void;
  onObjSearchChange?: (objSearch: any) => void;
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [selectedNotice, setSelectedNotice] =
    useState<CompletedNoticeState | null>(null);
  const noticeSliderRef = useRef(null);
  const [showDeleteNotice, setShowDeleteNotice] = useState(false);
  const [selectedIdNotice, setSelectedIdNotice] = useState<number | null>(null);

  const { deleteNoticeAPI } = useHandover();

  const {
    data,
    pageSize,
    currentPage,
    objSearch,
    refreshTable,
    setPageSize,
    setCurrentPage,
    setObjSearch,
    setRefreshTable,
    getCompletedNoticeAPI,
  } = useCompletedNotice();

  useEffect(() => {
    if (pageSize && currentPage) {
      getCompletedNoticeAPI();
    }
  }, [pageSize, currentPage, objSearch]);

  useEffect(() => {
    if (onObjSearchChange) {
      onObjSearchChange(objSearch);
    }
  }, [objSearch, onObjSearchChange]);

  const handleDeleteNotice = useCallback(async () => {
    if (!selectedIdNotice) return;
    // ★ [SEC-11a ② · 2026-09-07 턴 J · 차선 C] **거절을 삼키지 않는다.**
    try {
      const { success, message } = await deleteNoticeAPI(selectedIdNotice);
      if (success) {
        ToastTopHelper.success(message);
        getCompletedNoticeAPI();
        getSliderDataAPI();
      } else {
        ToastTopHelper.error(message);
      }
    } catch (error) {
      ToastTopHelper.error(failureLine('CompletedNotice.delete', error));
    } finally {
      // 확인 상자는 **어느 갈래에서도 닫힌다.** 열린 채로 남은 상자는 고장으로 읽힌다.
      setShowDeleteNotice(false);
    }
  }, [
    selectedIdNotice,
    deleteNoticeAPI,
    getCompletedNoticeAPI,
    getSliderDataAPI,
  ]);

  const COLUMNS = useMemo(
    () =>
      COLUMNS_COMPLETED_NOTICE.map((column) => {
        if (column.accessor === 'status') {
          return {
            ...column,
            filterOptions: [
              { label: t('Select'), value: '' },
              { label: t('Complete'), value: 'Complete' },
              { label: t('Delete'), value: 'Delete' },
            ],
            cell: (info: { row: { original: { status: string } } }) => {
              return formatIsProcessed(t, theme, info.row.original.status);
            },
          };
        }
        return column;
      }),
    [t, theme],
  );

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  const handleClickRow = useCallback(
    (row: CompletedNoticeState) => {
      setOpenOffcanvas(true);
      setSelectedNotice(row);
      setSelectedIdNotice(row.id);
    },
    [setOpenOffcanvas, setSelectedNotice],
  );

  const handleOpenOffcanvas = useCallback(
    (boolean: boolean) => {
      setOpenOffcanvas(boolean);
    },
    [setOpenOffcanvas],
  );

  return (
    <Main>
      <NoticeSlider
        ref={noticeSliderRef}
        items={sliderData}
        handleRefresh={() => {
          getCompletedNoticeAPI();
          getSliderDataAPI();
          setOpenOffcanvas(false);
        }}
      />

      <CustomizableTable
        subTable
        stickyHeader
        useSystemSetting
        notUseGroupColumn
        notShowSelectRow
        availableHeight={spaceTableHeight}
        columns={COLUMNS}
        data={data}
        objSearch={objSearch}
        setObjSearch={setObjSearch}
        refreshTable={refreshTable}
        setRefreshTable={setRefreshTable}
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        pageSize={pageSize}
        setPageSize={setPageSize}
        onClickRow={handleClickRow}
        offcanvas={openOffcanvas}
        setOpenOffcanvas={handleOpenOffcanvas}
      />

      <EditNotice
        noticeId={selectedNotice?.id || null}
        open={openOffcanvas}
        onClose={() => setOpenOffcanvas(false)}
        isCompletedNotice={true}
        handleRefresh={() => {
          getCompletedNoticeAPI();
          getSliderDataAPI();
        }}
      />
      <CustomModal
        title={t('handover.Delete Notice')}
        show={showDeleteNotice}
        onHide={() => setShowDeleteNotice(false)}
        id="delete-completed-notice"
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
              onClick={handleDeleteNotice}
              id="delete-notice-button"
            />,
          ]}
          rightButtons={[
            <CustomBtn
              variant="outline"
              color="secondary"
              size="lg"
              label={t('handover.Cancel')}
              type="button"
              onClick={() => setShowDeleteNotice(false)}
            />,
          ]}
        />
      </CustomModal>
    </Main>
  );
};
