import { Box } from '@mui/material';
import dayjs, { Dayjs } from 'dayjs';
import { t } from 'i18next';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { BsEye } from 'react-icons/bs';
import { useLocation } from 'react-router-dom';
import {
  ActionBtn,
  Container,
  CustomBtn,
  CustomInputHookForm,
  CustomizableTable,
  CustomModal,
  Main,
  ToastTopHelper,
  useCalculateHeight,
  useConfigSystem,
  useLoadingContext,
  useTheme,
  useUserInfo,
} from 'rj-core';

import ErrorImage from '@/assets/images/no-image.png';
import Truncate from '@/components/truncate/Truncate';
import { getDateFormatStringForDayjs } from '@/features/Dashboard/utils/formatDateTime';
import { useSurveillanceProfile } from '@/features/surveillanceProfile/hooks/useSurveillanceProfile';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { formatEnabled } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import { ProfileDetailModal } from '../../CompletedTab/components/ProfileDetailModal';
import TimelineView from './components/TimelineView';

const DeviceImage = React.memo<{
  imageUrl: string;
  alt: string;
}>(({ imageUrl, alt }) => {
  const handleImageError = useCallback(
    (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
      (e.target as HTMLImageElement).src = ErrorImage;
    },
    [],
  );

  return (
    <Box p={'0.375rem 0.25rem'}>
      <img
        src={imageUrl}
        alt={alt}
        onError={handleImageError}
        className="list-device__image"
        style={{
          width: '100%',
          aspectRatio: '2/1',
          objectFit: 'cover',
        }}
      />
    </Box>
  );
});

DeviceImage.displayName = 'DeviceImage';

const SurveillanceProfileTabOptimized = () => {
  const { approveSurveillanceProfileAPI, rejectSurveillanceProfileAPI } =
    useSurveillanceProfile();
  const [objSearch, setObjSearch] = useState({});
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const [theme] = useTheme();
  const methods = useForm({
    defaultValues: {
      reason: '',
    },
  });
  const {
    control,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { isValid, isSubmitting },
  } = methods;

  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [showRejectModal, setShowRejectModal] = useState<{
    id: number | null;
    show: boolean;
  }>({ id: null, show: false });
  const { getListSurveillanceProfileAPI } = useSurveillanceProfile();

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  // use for save searchcondition
  const location = useLocation();
  const { data: dataSearchCondition } = location.state || {};

  useEffect(() => {
    if (dataSearchCondition) {
      setObjSearch(dataSearchCondition);
    }
  }, [dataSearchCondition]);
  //end
  const { showLoading, hideLoading } = useLoadingContext();

  const fetchData = async ({
    objSearch,
    pageSize,
    currentPage,
  }: {
    objSearch: any;
    pageSize: number;
    currentPage: number;
  }) => {
    showLoading();
    const { success, data, message } = await getListSurveillanceProfileAPI({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearch,
      status__code: 'pending_approval',
    });

    if (success) {
      setData(data);
    }
    if (!success) {
      ToastTopHelper.error(message || 'Expected error');
    }
    hideLoading();
  };

  useEffect(() => {
    if (pageSize) {
      fetchData({ objSearch, pageSize, currentPage });
    }
  }, [pageSize, currentPage, objSearch]);

  const handleSelectionRows = (selectedData: any) => {
    setSelectedRows(selectedData);
  };

  const headerPageRef = useRef(null);
  const searchCardRef = useRef(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchCardRef],
    additionalHeights: [remToPx(8)],
  });

  const [statusType, setItemType] = useState<any[]>([]);
  const { useFetchOptions, getOptionsByModel } = useCommonAPI();

  const purposeTypeConfig = useMemo(
    () => ({
      type: 'model' as const,
      params: { name_modal: 'MissionPurpose', search_field: 'name' },
      defaultLabel: t('Select'),
    }),
    [],
  );
  const purposeType = useFetchOptions(getOptionsByModel, purposeTypeConfig);

  useEffect(() => {
    const fetchStatusType = async () => {
      try {
        const fetchFunction = getOptionsByModel({
          name_modal: 'devicestatus',
          search_field: 'name',
        });
        const { options } = await fetchFunction('', [], {
          page: 1,
          page_size: 1000,
        });
        if (options) {
          setItemType([{ label: t('Select'), value: '' }, ...options]);
        }
      } catch (error) {
        console.log('Error fetch status type', error);
      }
    };
    fetchStatusType();
  }, [statusType.length < 0]);

  const [selectedRow, setSelectedRow] = useState(null);
  const [showDetailProfileModal, setShowDetailProfileModal] =
    useState<boolean>(false);

  // Timeline view states
  const [viewType, setViewType] = useState<'profile' | 'drone'>('profile');
  const userInfo = useUserInfo();
  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];
  const dateFormat = getDateFormatStringForDayjs(
    userInfo?.settings?.date_format__code ??
    unitPreferences?.date_format ??
    'DD/MM/YYYY',
  );
  const [selectedDate, setSelectedDate] = useState<Dayjs | string>(
    dayjs().format('YYYY-MM-DD'),
  );

  const handleApproveSurveillanceProfile = useCallback(
    async (id: number) => {
      const { success, message } = await approveSurveillanceProfileAPI(id);
      if (success) {
        ToastTopHelper.success(message);
        setData((prevData) => ({
          ...prevData,
          data: prevData.data.filter((item: any) => item.id !== id),
        }));
        setRefreshTable(true);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [approveSurveillanceProfileAPI],
  );

  const handleRejectSurveillanceProfile = useCallback(
    async (id: number, reason: string) => {
      const { success, message } = await rejectSurveillanceProfileAPI(
        id,
        reason,
      );
      if (success) {
        ToastTopHelper.success(message);
        setShowRejectModal({ id: null, show: false });
        reset();
        setData((prevData) => ({
          ...prevData,
          data: prevData.data.filter((item: any) => item.id !== id),
        }));
        setRefreshTable(true);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [rejectSurveillanceProfileAPI],
  );

  const handleEventClick = useCallback((event: any) => {
    setShowDetailProfileModal(true);
    fetchDetailSurveillanceProfile(event?.id as number);
  }, []);

  const HistoryBehaviorColumns = [
    {
      Header: t(' '),
      accessor: 'action',
      cell: (row: any) => (
        <div
          className="special-label"
          onClick={(e) => {
            e.stopPropagation();
            setShowDetailProfileModal(true);
            fetchDetailSurveillanceProfile(row?.row?.original?.id as number);
            setSelectedRow(row);
          }}
        >
          <BsEye size={16} />
        </div>
      ),
      customStyle: { maxWidth: 5, textAlign: 'center' },
      enableSorting: false,
      enableColumnFilter: false,
    },
    {
      Header: 'Profile ID',
      accessor: 'id',
      enableSorting: true,
      enableColumnFilter: true,
      customStyle: {
        width: '8rem',
      },
    },
    {
      Header: 'Profile Name',
      accessor: 'name',
      enableSorting: true,
      enableColumnFilter: true,
      cell: (info: any) => {
        return info.getValue() ? (
          <Truncate
            content={info.getValue()}
            tooltipContent={info.getValue()}
          />
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Purpose',
      accessor: 'purpose__name',
      enableSorting: true,
      enableColumnFilter: true,
      filterVariant: 'select',
      filterOptions:
        purposeType.length > 0
          ? purposeType?.map((item: any) => ({
            label: item.label,
            value:
              item.label == 'Select' ||
                item.label == '선택' ||
                item.label == 'เลือก'
                ? ''
                : item.label,
          }))
          : [],
      cell: (info: any) => {
        return info.getValue() ? (
          <Truncate
            content={info.getValue()}
            tooltipContent={info.getValue()}
          />
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Created Date',
      accessor: 'created_on',
      filterVariant: 'datetime',
      enableSorting: true,
      enableColumnFilter: true,
    },
    {
      Header: 'Start Time',
      accessor: 'start_time',
      filterVariant: 'datetime',
      enableSorting: true,
      enableColumnFilter: true,
    },
    {
      Header: 'End Time',
      accessor: 'estimated_end_time',
      filterVariant: 'datetime',
      enableSorting: true,
      enableColumnFilter: true,
    },
    {
      Header: 'Total Distance',
      accessor: 'total_distance',
      enableSorting: true,
      enableColumnFilter: true,
      cell: (info: any) => {
        return info.getValue() ? (
          <Truncate
            content={info.getValue()}
            tooltipContent={info.getValue()}
          />
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Estimated Time',
      accessor: 'estimated_time',
      enableSorting: true,
      enableColumnFilter: true,
      cell: (info: any) => {
        return info.getValue() ? (
          <Truncate
            content={info.getValue()}
            tooltipContent={info.getValue()}
          />
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Log',
      accessor: 'mission__log_collection',
      enableSorting: true,
      enableColumnFilter: true,
      filterVariant: 'checkbox',
      filterOptions: ['True', 'False'],
      customStyle: {
        width: '7rem',
      },
      cell: (info: any) => formatEnabled(info.getValue()),
    },
    {
      Header: 'Record',
      accessor: 'mission__video_recording',
      enableSorting: true,
      enableColumnFilter: true,
      filterVariant: 'checkbox',
      filterOptions: ['True', 'False'],
      customStyle: {
        width: '7rem',
      },
      cell: (info: any) => formatEnabled(info.getValue()),
    },
    {
      Header: 'Analysis',
      accessor: 'mission__video_analysis',
      enableSorting: true,
      enableColumnFilter: true,
      filterVariant: 'checkbox',
      filterOptions: ['True', 'False'],
      customStyle: {
        width: '7rem',
      },
      cell: (info: any) => formatEnabled(info.getValue()),
    },
    {
      Header: 'Created By',
      accessor: 'created_by_full_name',
      enableSorting: true,
      enableColumnFilter: true,
    },
    {
      Header: 'Operator',
      accessor: 'operator_full_name',
      enableSorting: true,
      enableColumnFilter: true,
    },
    {
      Header: t(' '),
      accessor: 'action',
      enableSorting: false,
      enableColumnFilter: false,
      notUseConfigTable: true,
      cell: (row: any) => {
        const rowId = row?.row?.original?.id;
        return (
          <div
            onClick={(e) => {
              e.stopPropagation();
            }}
            style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}
          >
            <CustomBtn
              variant="outline"
              color="primary"
              label={t('Approve')}
              onClick={() => handleApproveSurveillanceProfile(rowId)}
            />
            <CustomBtn
              variant="outline"
              color="primary"
              label={t('Reject')}
              onClick={() => setShowRejectModal({ id: rowId, show: true })}
            />
          </div>
        );
      },
    },
  ];

  const {
    fetchDetailSurveillanceProfile,
    detailSurveillanceProfile,
    markerData,
  } = useSurveillanceProfile();

  const droneRoutes = useMemo(() => {
    if (
      !detailSurveillanceProfile?.drone_assignments ||
      detailSurveillanceProfile?.drone_assignments.length === 0
    ) {
      return [];
    }

    return detailSurveillanceProfile?.drone_assignments.map((assignment) => ({
      route_path:
        assignment.route_path?.map((item) => ({
          lat: item.latitude,
          lng: item.longitude,
          name: item.name,
          altitude: item.altitude ?? 0,
          command: Object.keys(item?.command_name)?.[0] ?? 'WAYPOINT',
          frame: item?.frame_name ?? 'FRAME',
          param_1: Object.values(item?.params)?.[0]?.[0] ?? 0,
          param_2: Object.values(item?.params)?.[0]?.[1] ?? 0,
          param_3: Object.values(item?.params)?.[0]?.[2] ?? 0,
          param_4: Object.values(item?.params)?.[0]?.[3] ?? 0,
        })) || [],
      device: {
        id: assignment.device__id,
        name: '',
        color: assignment.color,
      },
    }));
  }, [detailSurveillanceProfile?.drone_assignments]);

  return (
    <Container
      id="list-device"
      isOpenCanvas={openOffcanvas}
    >
      <Main>
        <Box
          sx={{
            height: spaceTableHeight || 'calc(100vh - 200px)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <TimelineView
            viewType={viewType}
            onViewTypeChange={setViewType}
            selectedDate={selectedDate}
            onDateChange={(date) => setSelectedDate(date || dayjs())}
            onEventClick={handleEventClick}
          />

          <div className="list-device__table-container">
            <CustomizableTable
              subTable
              stickyHeader
              notUseGroupColumn
              notShowSelectRow
              useSystemSetting
              availableHeight={spaceTableHeight}
              columns={HistoryBehaviorColumns}
              data={data}
              objSearch={objSearch}
              setObjSearch={setObjSearch}
              onSelectedRows={handleSelectionRows}
              refreshTable={refreshTable}
              setRefreshTable={setRefreshTable}
              currentPage={currentPage}
              setCurrentPage={setCurrentPage}
              pageSize={pageSize}
              setPageSize={setPageSize}
              offcanvas={openOffcanvas}
              setOpenOffcanvas={(boolean: boolean) => {
                setOpenOffcanvas(boolean);
              }}
            />
          </div>
        </Box>
      </Main>
      <ProfileDetailModal
        show={showDetailProfileModal}
        onHide={() => setShowDetailProfileModal(false)}
        detailData={detailSurveillanceProfile}
        markerData={markerData}
        droneRoutes={droneRoutes}
      />
      <CustomModal
        title={t('Reject Profile')}
        show={showRejectModal.show}
        onHide={() => setShowRejectModal({ id: null, show: false })}
      >
        <FormProvider {...methods}>
          <form
            onSubmit={handleSubmit((values) =>
              handleRejectSurveillanceProfile(
                showRejectModal.id as number,
                values.reason,
              ),
            )}
          >
            <div style={{ width: '40rem' }}>
              <p>{t('Please enter the reason for rejecting this profile.')}</p>

              <CustomInputHookForm
                name="reason"
                placeholder={t('Reason')}
              />
            </div>
            <ActionBtn
              styles={{
                maxWidth: '100%',
                margin: 'unset',
                padding: '0.5rem 0 1rem 0',
              }}
              leftButtons={[
                <CustomBtn
                  variant="contained"
                  color="primary"
                  size="lg"
                  type="submit"
                  loading={isSubmitting || !isValid}
                  disabled={isSubmitting || !watch('reason')}
                  label={t('Confirm')}
                />,
              ]}
              rightButtons={[
                <CustomBtn
                  type="button"
                  variant="outline"
                  color="secondary"
                  size="lg"
                  onClick={() => {
                    setShowRejectModal({ id: null, show: false });
                  }}
                  label={t('Cancel')}
                />,
              ]}
            />
          </form>
        </FormProvider>
      </CustomModal>
    </Container>
  );
};
export default SurveillanceProfileTabOptimized;
