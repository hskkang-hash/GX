import dayjs, { Dayjs } from 'dayjs';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
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

import { ACTION_TYPE_BTN } from '../../../../../configs/Constant';
import i18n from '../../../../../i18n';
import { CustomRoutes } from '../../../../../services/API';
import { remToPx } from '../../../../../utils/utils';
import { NoticeSlider } from '../../../components/NoticeSlider';
import { SearchCardDateTime } from '../../../components/SearchCardDateTime';
import { useDateFormat, useTimezoneCode } from '../../../hooks/useDateFormat';
import {
  HandoverManagementState,
  HandoverShiftState,
  NoticeManagementState,
} from '../../../types';
import { formatDate } from '../../../utils/dateFormat';
import { CreateHandoverModal } from './components/CreateHandoverModal';
import { useHandoverManagement } from './hooks/useHandoverManagement';
import { failureLine } from '@/features/session/apiFailure';

const SHIFT_STATUS = {
  HAVE_SHIFTS: 'have_shifts',
  NO_SHIFTS: 'not_have_shifts',
};

export const HandoverManagement = ({
  headerPageRef,
  openOffcanvas,
  setOpenOffcanvas,
  showCreateHandover,
  setShowCreateHandover,
  sliderData,
  getSliderDataAPI,
  searchDateTime,
  setSearchDateTime,
}: {
  headerPageRef: React.RefObject<HTMLElement | null>;
  openOffcanvas: boolean;
  setOpenOffcanvas: (boolean: boolean) => void;
  showCreateHandover: boolean;
  setShowCreateHandover: (boolean: boolean) => void;
  sliderData: NoticeManagementState[];
  getSliderDataAPI: () => void;
  searchDateTime: {
    startDate: Dayjs | null;
    endDate: Dayjs | null;
  };
  setSearchDateTime: (data: {
    startDate: Dayjs | null;
    endDate: Dayjs | null;
  }) => void;
}) => {
  const { t } = useTranslation();
  const { dateFormat } = useDateFormat();
  const { timezoneCode } = useTimezoneCode();

  const navigate = useNavigate();
  const noticeSliderRef = useRef<HTMLDivElement | null>(null);
  const searchCardDateTimeRef = useRef<HTMLDivElement | null>(null);

  const [showCreateLog, setShowCreateLog] = useState(false);
  const [createShiftLogData, setCreateShiftLogData] = useState<{
    shift_id: number;
    date: string;
  } | null>(null);

  const [selectedRows, setSelectedRows] = useState<HandoverManagementState[]>(
    [],
  );
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
    getHandoverManagementAPI,
    deleteShiftHandoverAPI,
    createShiftHandoverAPI,
    getHandoverShiftAPI,
    shiftList,
  } = useHandoverManagement();

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, noticeSliderRef, searchCardDateTimeRef],
    additionalHeights: [remToPx(10)],
  });

  useEffect(() => {
    getHandoverShiftAPI();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (
      pageSize &&
      currentPage &&
      searchDateTime.startDate &&
      searchDateTime.endDate
    ) {
      getHandoverManagementAPI({
        start_date_time: searchDateTime.startDate.format('YYYY-MM-DD'),
        end_date_time: searchDateTime.endDate.format('YYYY-MM-DD'),
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageSize, currentPage, objSearch]);

  const handleClickRow = useCallback(
    (row: HandoverManagementState) => {
      if (!row.id) return;
      navigate(
        CustomRoutes.handover.subRoutes.createShiftLogHandover.path.replace(
          ':id',
          row.id.toString(),
        ),
        { state: { date: row.date } },
      );
    },
    [navigate],
  );

  const handleSelectionRows = useCallback((rows: HandoverManagementState[]) => {
    setSelectedRows(rows);
  }, []);

  const handleOpenOffcanvas = useCallback(
    (boolean: boolean) => {
      setOpenOffcanvas(boolean);
    },
    [setOpenOffcanvas],
  );

  const handleDelete = useCallback(async () => {
    // ★ [SEC-11a ② · 2026-09-07 턴 J · 차선 C] **거절을 삼키지 않는다.**
    //   `try` 가 하나도 없던 파일이다. 접두 승격이 켜지면 이 `await` 는 예외로 끝나고,
    //   전역 `unhandledrejection` 처리기는 이 저장소에 0건이다 — 즉 **조용히 멈춘다.**
    const ids = selectedRows.map((item) => item.id);
    try {
    const { success, message, failed } = await deleteShiftHandoverAPI(ids);
    if (success && failed.length === 0) {
      ToastTopHelper.success(message);
      setRefreshTable(true);
      setSelectedRows([]);
      getHandoverManagementAPI({
        start_date_time: searchDateTime.startDate?.format('YYYY-MM-DD') || '',
        end_date_time: searchDateTime.endDate?.format('YYYY-MM-DD') || '',
      });
    } else if (failed.length > 0) {
      ToastTopHelper.warning(message);
      setRefreshTable(true);
      setSelectedRows([]);
      getHandoverManagementAPI({
        start_date_time: searchDateTime.startDate?.format('YYYY-MM-DD') || '',
        end_date_time: searchDateTime.endDate?.format('YYYY-MM-DD') || '',
      });
    } else {
      ToastTopHelper.error(message);
    }
    } catch (error) {
      ToastTopHelper.error(failureLine('HandoverManagement.delete', error));
    }
  }, [
    deleteShiftHandoverAPI,
    selectedRows,
    setRefreshTable,
    getHandoverManagementAPI,
    searchDateTime,
  ]);

  const handleSearch = useCallback(
    (data: { startDate: Dayjs; endDate: Dayjs }) => {
      let startDate: Dayjs;
      let endDate: Dayjs;

      if (data.startDate && data.endDate) {
        // Both dates provided, use them directly
        startDate = data.startDate;
        endDate = data.endDate;
      } else if (data.startDate) {
        // Only start date provided, set end date to today
        startDate = data.startDate;
        endDate = dayjs();
      } else if (data.endDate) {
        // Only end date provided, set start date to 7 days before
        startDate = data.endDate.subtract(7, 'day');
        endDate = data.endDate;
      } else {
        // No dates provided, use default: 7 days ago to today
        startDate = dayjs().subtract(7, 'day');
        endDate = dayjs();
      }

      // Validate dates before updating state and calling API
      if (!startDate.isValid() || !endDate.isValid()) {
        console.error('Invalid dates:', { startDate, endDate });
        return;
      }

      // Update state first
      setSearchDateTime({
        startDate,
        endDate,
      });

      // Call API with validated dates in YYYY-MM-DD format
      getHandoverManagementAPI({
        start_date_time: startDate.format('YYYY-MM-DD'),
        end_date_time: endDate.format('YYYY-MM-DD'),
      });
    },
    [getHandoverManagementAPI, setSearchDateTime],
  );

  const handleOnClickCreate = useCallback(
    (id: number, date: string) => () => {
      setCreateShiftLogData({
        shift_id: id,
        date: date,
      });
      setShowCreateLog(true);
    },
    [setCreateShiftLogData, setShowCreateLog],
  );

  const COLUMNS = useMemo(
    () => [
      {
        Header: 'Date',
        accessor: 'date',
        filterVariant: 'datetime',
        cell: (info: {
          row: {
            original: HandoverManagementState;
          };
        }) => {
          return (
            <div>
              {formatDate(
                info.row.original.date,
                dateFormat,
                i18n.language,
                timezoneCode,
              )}
            </div>
          );
        },
      },
      {
        Header: 'Status',
        accessor: 'status',
        enableColumnFilter: false,
        enableSorting: false,
        customStyle: {
          width: `${shiftList.length * 10.5}rem`,
        },
        cell: (info: {
          row: {
            original: HandoverManagementState & {
              status: string;
              notShowCheckbox?: boolean;
            };
          };
        }) => {
          switch (info.row.original.status) {
            case SHIFT_STATUS.NO_SHIFTS:
              return (
                <div>
                  {i18n.language === 'en'
                    ? `${info.row.original.shift__name} log for ${formatDate(info.row.original.date, dateFormat, i18n.language, timezoneCode)}`
                    : i18n.language === 'ko'
                      ? `${formatDate(info.row.original.date, dateFormat, i18n.language, timezoneCode)}에 대한 ${info.row.original.shift__name} 로그`
                      : `${formatDate(info.row.original.date, dateFormat, i18n.language, timezoneCode)} ลงรายการ ${info.row.original.shift__name}`}
                </div>
              );
            case SHIFT_STATUS.HAVE_SHIFTS:
              return (
                <div className="d-flex gap-3">
                  {info.row.original?.data?.map(
                    (
                      item: HandoverShiftState,
                      index: number,
                    ): React.ReactNode => {
                      return (
                        <CustomBtn
                          key={index}
                          actionType={ACTION_TYPE_BTN.CREATE}
                          label={
                            i18n.language === 'en'
                              ? t('handover.Create') + ` ${item.name}`
                              : `${item.name} ` + t('handover.Create')
                          }
                          id="add-button"
                          variant="outline"
                          onClick={handleOnClickCreate(
                            item.handover_shift,
                            info.row.original.date,
                          )}
                          color="primary"
                          size="sm"
                        />
                      );
                    },
                  )}
                </div>
              );

            default:
              return <></>;
          }
        },
      },
      {
        Header: 'Number of contents',
        accessor: 'total_content',
      },
      {
        Header: 'Created Date',
        accessor: 'created_time',
        filterVariant: 'datetime',
      },
      {
        Header: 'Writer',
        accessor: 'creator__full_name',
      },
    ],
    [t, handleOnClickCreate, dateFormat, shiftList],
  );

  const handleCreateShiftLog = useCallback(async () => {
    if (createShiftLogData?.date && createShiftLogData?.shift_id) {
      // ★ [SEC-11a ② · 턴 J · 차선 C] 만들기 단추가 **조용히 실패하지 않게** 한다.
      try {
        const { success, message } =
          await createShiftHandoverAPI(createShiftLogData);
        if (success) {
          ToastTopHelper.success(message);
          setShowCreateLog(false);
          getHandoverManagementAPI({
            start_date_time: searchDateTime.startDate?.format('YYYY-MM-DD') || '',
            end_date_time: searchDateTime.endDate?.format('YYYY-MM-DD') || '',
          });
        } else {
          ToastTopHelper.error(message);
        }
      } catch (error) {
        ToastTopHelper.error(failureLine('HandoverManagement.createShiftLog', error));
      }
    }
  }, [
    createShiftHandoverAPI,
    createShiftLogData,
    setShowCreateLog,
    getHandoverManagementAPI,
    searchDateTime,
  ]);

  const handleCreateHandover = useCallback(
    async (data: { date: string; shift_id: number | null }) => {
      // ★ [SEC-11a ② · 턴 J · 차선 C] 같은 자리 둘째 — 여기도 `try` 가 없었다.
      try {
        const { success, message } = await createShiftHandoverAPI(data);
        if (success) {
          ToastTopHelper.success(message);
          setShowCreateHandover(false);
          getHandoverManagementAPI({
            start_date_time: searchDateTime.startDate?.format('YYYY-MM-DD') || '',
            end_date_time: searchDateTime.endDate?.format('YYYY-MM-DD') || '',
          });
        } else {
          ToastTopHelper.error(message);
        }
      } catch (error) {
        ToastTopHelper.error(failureLine('HandoverManagement.createHandover', error));
      }
    },
    [
      createShiftHandoverAPI,
      getHandoverManagementAPI,
      searchDateTime,
      setShowCreateHandover,
    ],
  );

  const handleNavigateDuty = useCallback(() => {
    const ids = selectedRows.map((row) => row.id);
    navigate(CustomRoutes.handover.subRoutes.handoverDutyDetail.path, {
      state: { ids: ids },
    });
  }, [navigate, selectedRows]);

  return (
    <Main>
      <NoticeSlider
        ref={noticeSliderRef}
        items={sliderData}
        handleRefresh={() => {
          getSliderDataAPI();
          setOpenOffcanvas(false);
        }}
      />
      <SearchCardDateTime
        ref={searchCardDateTimeRef}
        value={searchDateTime}
        setValue={setSearchDateTime}
        handleSearch={handleSearch}
      />
      <CustomizableTable
        stickyHeader
        useSystemSetting={true}
        subTable={true}
        availableHeight={spaceTableHeight}
        columns={COLUMNS}
        buttons={[
          <CustomBtn
            label={t('handover.Delete')}
            type="button"
            variant="outline"
            color="primary"
            size="sm"
            disabled={selectedRows.length === 0}
            actionType={ROLE_PERMISSION.DELETE}
            onClick={handleDelete}
          />,
          <CustomBtn
            label={t('handover.Handover Duty Detail')}
            type="button"
            variant="outline"
            color="primary"
            size="sm"
            disabled={selectedRows.length === 0}
            onClick={handleNavigateDuty}
          />,
        ]}
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
        onSelectedRows={handleSelectionRows}
        offcanvas={openOffcanvas}
        setOpenOffcanvas={handleOpenOffcanvas}
      />
      <CustomModal
        title={t('handover.Create shift log')}
        show={showCreateLog}
        onHide={() => setShowCreateLog(false)}
        id="create-shift-log"
      >
        <div className="text">
          {t('handover.Would you like to create a shift log?')}
        </div>

        <ActionBtn
          leftButtons={[
            <CustomBtn
              variant="outline"
              color="primary"
              size="lg"
              label={t('handover.Ok')}
              onClick={handleCreateShiftLog}
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
              onClick={() => setShowCreateLog(false)}
            />,
          ]}
        />
      </CustomModal>
      <CreateHandoverModal
        show={showCreateHandover}
        onHide={() => setShowCreateHandover(false)}
        onSubmit={handleCreateHandover}
        shiftList={shiftList}
      />
    </Main>
  );
};
