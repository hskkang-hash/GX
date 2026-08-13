import { yupResolver } from '@hookform/resolvers/yup';
import { Box } from '@mui/material';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import { useLocation, useNavigate } from 'react-router-dom';
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
  useLoadingContext,
} from 'rj-core';
import * as yup from 'yup';

import ErrorImage from '@/assets/images/no-image.png';
import Truncate from '@/components/truncate/Truncate';
import { useSurveillanceProfile } from '@/features/surveillanceProfile/hooks/useSurveillanceProfile';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { CustomRoutes } from '@/services/API';
import { formatEnabled } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import { ProfileDetailModal } from '../../CompletedTab/components/ProfileDetailModal';

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

const SurveillanceGCSTab = () => {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  console.log('t', t);
  console.log('i18n', i18n.language);
  const { cancelSurveillanceProfileAPI } = useSurveillanceProfile();
  const [objSearch, setObjSearch] = useState({});
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);

  const methods = useForm({
    defaultValues: {
      reason: t('The drone encountered an issue during the mission'),
    },
    resolver: yupResolver(
      yup.object().shape({
        reason: yup.string().required(t('This field is required.')),
      }),
    ),
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
  const [showCancelModal, setShowCancelModal] = useState<{
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

  console.log('data_surveillance_profile', data);

  // use for save searchcondition
  const location = useLocation();
  const { data: dataSearchCondition } = location.state || {};

  useEffect(() => {
    if (dataSearchCondition) {
      setObjSearch(dataSearchCondition);
    }
  }, [dataSearchCondition]);
  //end

  useEffect(() => {
    if (showCancelModal.show) {
      reset({
        reason: t('The drone encountered an issue during the mission'),
      });
    }
  }, [showCancelModal.show, reset, t]);

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
      status__code: 'in_progress',
    });
    console.log('data_surveillance_profile', data);

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
        console.log('result_fetch_status_type', options);
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

  const handleSurveillance = useCallback(
    (profileId: number, groupId: number, missionName: string) => {
      // Navigate to surveillance GCS page with groupId as URL parameter
      navigate(
        `${CustomRoutes.surveyProfile.subRoutes.surveillanceGCS.path}?profileId=${profileId}&groupId=${groupId}&mission=${missionName}&tab=processing`,
      );
    },
    [navigate],
  );

  const handleCancelSurveillance = async (
    profile_id: number,
    reason: string,
  ) => {
    try {
      const { success, message } = await cancelSurveillanceProfileAPI(
        profile_id,
        reason,
      );
      if (success) {
        ToastTopHelper.success(message);
        setShowCancelModal({ id: null, show: false });
        setRefreshTable(true);
        fetchData({ objSearch, pageSize, currentPage });
        reset();
      } else {
        ToastTopHelper.error(message);
      }
    } catch (error) {
      ToastTopHelper.error(
        error?.response?.data?.message ||
          t('Surveillance profile cancellation failed'),
      );
    }
  };

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
      customStyle: { maxWidth: 20, textAlign: 'center' },
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
      Header: 'Actual Start Time',
      accessor: 'actual_start_time',
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
      Header: 'Operator',
      accessor: 'operator_full_name',
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
      Header: t(' '),
      accessor: 'action',
      enableSorting: false,
      enableColumnFilter: false,
      notUseConfigTable: true,
      customStyle: {
        width: '15rem',
      },
      cell: (row: any) => {
        const rowId = row?.row?.original?.id;
        const profileGroupId = row?.row?.original?.group_id;
        const profileId = row?.row?.original?.id;
        const missionName = row?.row?.original?.mission__name;
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
              label={t('Surveillance')}
              onClick={() =>
                handleSurveillance(profileId, profileGroupId, missionName)
              }
            />
            <CustomBtn
              variant="outline"
              color="primary"
              label={t('Cancel')}
              onClick={() => setShowCancelModal({ id: rowId, show: true })}
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
  console.log('detailSurveillanceProfile', detailSurveillanceProfile);
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
          frame: item.frame_name ?? 'FRAME',
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
        showActualStartTime
      />
      <CustomModal
        title={t('Cancel Profile')}
        show={showCancelModal.show}
        onHide={() => setShowCancelModal({ id: null, show: false })}
      >
        <FormProvider {...methods}>
          <form
            onSubmit={handleSubmit((values) =>
              handleCancelSurveillance(
                showCancelModal.id as number,
                values.reason,
              ),
            )}
          >
            <div style={{ width: '40rem' }}>
              <p>
                {t(
                  'Please tell us the reason why you want to cancel this profile.',
                )}
              </p>
              <CustomInputHookForm
                name="reason"
                placeholder={t('Reason')}
              />
            </div>
            <ActionBtn
              leftButtons={[
                <CustomBtn
                  type="submit"
                  variant="contained"
                  color="primary"
                  size="lg"
                  label={t('Confirm')}
                  loading={isSubmitting}
                  disabled={isSubmitting || !watch('reason')}
                />,
              ]}
              rightButtons={[
                <CustomBtn
                  type="button"
                  variant="outline"
                  color="secondary"
                  size="lg"
                  label={t('Cancel')}
                  onClick={() => setShowCancelModal({ id: null, show: false })}
                />,
              ]}
            />
          </form>
        </FormProvider>
      </CustomModal>
    </Container>
  );
};
export default SurveillanceGCSTab;
