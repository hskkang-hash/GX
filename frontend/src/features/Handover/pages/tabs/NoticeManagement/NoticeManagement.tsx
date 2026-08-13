import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomizableTable,
  CustomModal,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import { remToPx } from '../../../../../utils/utils';
import { NoticeSlider } from '../../../components/NoticeSlider';
import { COLUMNS_NOTICE_MANAGEMENT } from '../../../dataExample';
import { NoticeManagementState } from '../../../types';
import EditNotice from './EditNotice';
import { useNoticeManagement } from './hooks/useNoticeManagement';

export const NoticeManagement = ({
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
    getNoticeManagementAPI,
    completeNoticeAPI,
  } = useNoticeManagement();

  const noticeSliderRef = useRef(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, noticeSliderRef],
    additionalHeights: [remToPx(8)],
  });

  const [showCompleteNotice, setShowCompleteNotice] = useState(false);
  const [selectedIdNotice, setSelectedIdNotice] = useState<number | null>(null);
  const [selectedNotice, setSelectedNotice] =
    useState<NoticeManagementState | null>(null);

  const handleCompleteNotice = useCallback(async () => {
    if (!selectedIdNotice) return;
    const { success, message } = await completeNoticeAPI(selectedIdNotice);
    if (success) {
      ToastTopHelper.success(message);
      setShowCompleteNotice(false);
      getNoticeManagementAPI();
      getSliderDataAPI();
      setOpenOffcanvas(false);
    } else {
      ToastTopHelper.error(message);
    }
  }, [completeNoticeAPI, selectedIdNotice, getNoticeManagementAPI]);

  const COLUMNS = useMemo(
    () => [
      ...COLUMNS_NOTICE_MANAGEMENT,
      {
        Header: ' ',
        accessor: 'action',
        enableSorting: false,
        enableColumnFilter: false,
        notUseConfigTable: true,
        cell: (row: { row: { original: { id: number } } }) => {
          return (
            <CustomBtn
              label={t('handover.Complete Notice')}
              variant="outline"
              color="primary"
              size="sm"
              actionType={ROLE_PERMISSION.UPDATE}
              onClick={() => {
                setShowCompleteNotice(true);
                setSelectedIdNotice(row.row.original.id);
              }}
            />
          );
        },
      },
    ],
    [t],
  );

  useEffect(() => {
    if (pageSize && currentPage) {
      getNoticeManagementAPI();
    }
  }, [pageSize, currentPage, objSearch]);

  useEffect(() => {
    if (onObjSearchChange) {
      onObjSearchChange(objSearch);
    }
  }, [objSearch, onObjSearchChange]);

  const handleClickRow = useCallback(
    (row: NoticeManagementState) => {
      setOpenOffcanvas(true);
      setSelectedNotice(row);
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
          getNoticeManagementAPI();
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
        handleRefresh={() => {
          getNoticeManagementAPI();
          getSliderDataAPI();
        }}
      />
      <CustomModal
        title={t('Complete Notice')}
        show={showCompleteNotice}
        onHide={() => setShowCompleteNotice(false)}
        id="complete-notice"
      >
        <div className="text">
          {t('Would you like to treat this notice as completed?')}
        </div>

        <ActionBtn
          leftButtons={[
            <CustomBtn
              variant="outline"
              color="primary"
              size="lg"
              label={t('Ok')}
              type="button"
              onClick={handleCompleteNotice}
              id="save-button"
            />,
          ]}
          rightButtons={[
            <CustomBtn
              variant="outline"
              color="secondary"
              size="lg"
              label={t('Cancel')}
              id="close-button"
              type="button"
              onClick={() => setShowCompleteNotice(false)}
            />,
          ]}
        />
      </CustomModal>
    </Main>
  );
};
