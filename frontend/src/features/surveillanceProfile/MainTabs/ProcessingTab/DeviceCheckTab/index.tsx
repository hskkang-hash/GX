import { Box } from '@mui/material';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import {
  ActionBtn,
  Container,
  CustomBtn,
  CustomizableTable,
  CustomModal,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
  useLoadingContext,
  useTheme,
} from 'rj-core';

import ArrowNoRepeat from '@/assets/images/ArrowNoRepeat';
import Truncate from '@/components/truncate/Truncate';
import Colors from '@/configs/Colors';
import { useSurveillanceProfile } from '@/features/surveillanceProfile/hooks/useSurveillanceProfile';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { formatEnabled } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import { ProfileDetailModal } from '../../CompletedTab/components/ProfileDetailModal';
import { CheckList } from './components/CheckList';

interface TableData {
  data: any[];
  totalItem: number;
  totalPage: number;
}

export default function DeviceCheckTab() {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const {
    fetchDetailSurveillanceProfile,
    detailSurveillanceProfile,
    markerData,
    getListSurveillanceProfileAPI,
    stopRepeatProfile,
    setDetailSurveillanceProfile,
  } = useSurveillanceProfile();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const searchCardRef = useRef<HTMLDivElement>(null);
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);

  const [data, setData] = useState<TableData>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [objSearch, setObjSearch] = useState<Record<string, unknown>>({});
  const [selectedRowForDetail, setSelectedRowForDetail] = useState<any | null>(
    null,
  );
  const [refreshChecklist, setRefreshChecklist] = useState<boolean>(false);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4), remToPx(1), 400],
  });
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

  const [isStopRepeatProfile, setIsStopRepeatProfile] = useState<boolean>(true);
  const [loadingStopRepeat, setLoadingStopRepeat] = useState<boolean>(false);

  const handleStopRepeatProfile = async (profile_id: number) => {
    setLoadingStopRepeat(true);
    setOpenModalStopRepeat({ id: undefined, show: false });
    const { success, message } = await stopRepeatProfile({
      profile_id: profile_id,
    });
    if (success) {
      ToastTopHelper.success(message);
      setRefreshTable(true);
      setData((prevData) => {
        const updatedData = prevData.data.map((item: any) =>
          item.id === profile_id ? { ...item, repeat_type__code: null } : item,
        );
        // Update selectedRowForDetail and isStopRepeatProfile if it is the stopped profile
        if (selectedRowForDetail?.id === profile_id) {
          const updatedRow = updatedData.find(
            (item: any) => item.id === profile_id,
          );
          if (updatedRow) {
            setTimeout(() => {
              setSelectedRowForDetail(updatedRow);
              setIsStopRepeatProfile(true);
            }, 0);
          }
        }
        return {
          ...prevData,
          data: updatedData,
        };
      });
    } else {
      ToastTopHelper.error(message);
      setRefreshTable(true);
    }
    setLoadingStopRepeat(false);
  };

  const [openModalStopRepeat, setOpenModalStopRepeat] = useState<{
    id: number | undefined;
    show: boolean;
  }>({ id: undefined, show: false });
  const [openModalDetailProfile, setOpenModalDetailProfile] = useState<{
    id: number | undefined;
    show: boolean;
  }>({ id: undefined, show: false });

  const COLUMNS = [
    {
      Header: t(' '),
      accessor: 'action',
      cell: (row: any) => {
        const isRepeatType = row?.row?.original?.repeat_type__code;
        const isRepeat = isRepeatType && isRepeatType !== 'none';
        return (
          <>
            {isRepeat && (
              <div
                className="special-label"
                onClick={(e) => {
                  e.stopPropagation();
                  setOpenModalStopRepeat({
                    id: row?.row?.original?.id,
                    show: true,
                  });
                }}
              >
                <ArrowNoRepeat
                  color={theme === 'dark' ? '#FFFFFF' : '#2D2E30'}
                />
              </div>
            )}
          </>
        );
      },
      customStyle: {
        width: '4rem',
        textAlign: 'center',
      },
      enableSorting: false,
      enableColumnFilter: false,
    },
    {
      Header: t(' '),
      accessor: 'action1',
      customStyle: { width: '3rem', textAlign: 'center' },
      cell: (row: any) => (
        <div
          className="special-label"
          onClick={(e) => {
            e.stopPropagation();
            setOpenModalDetailProfile({
              id: row?.row?.original?.id,
              show: true,
            });
            fetchDetailSurveillanceProfile(row?.row?.original?.id as number);
          }}
        >
          <BsEye size={16} />
        </div>
      ),
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
      cell: (info: any) => {
        return (
          <span
            style={{
              color:
                info.row?.original?.not_yet === true
                  ? Colors.Gray5
                  : theme === 'dark'
                    ? '#ececef'
                    : '#2D2E30',
            }}
          >
            {info.getValue() ? (
              <Truncate
                content={info.getValue()}
                tooltipContent={info.getValue()}
              />
            ) : (
              '-'
            )}
          </span>
        );
      },
    },
    {
      Header: 'Profile Name',
      accessor: 'name',
      enableSorting: true,
      enableColumnFilter: true,
      customStyle: {
        minWidth: '0.1rem',
      },
      cell: (info: any) => {
        return (
          <span
            style={{
              color:
                info.row?.original?.not_yet === true
                  ? Colors.Gray5
                  : theme === 'dark'
                    ? '#ececef'
                    : '#2D2E30',
            }}
          >
            {info.getValue() ? (
              <Truncate
                content={info.getValue()}
                tooltipContent={info.getValue()}
              />
            ) : (
              '-'
            )}
          </span>
        );
      },
    },
    {
      Header: 'Purpose',
      accessor: 'purpose__name',
      enableSorting: true,
      enableColumnFilter: true,
      filterVariant: 'select',
      customStyle: {
        minWidth: '0.1rem',
      },
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
        return (
          <span
            style={{
              color:
                info.row?.original?.not_yet === true
                  ? Colors.Gray5
                  : theme === 'dark'
                    ? '#ececef'
                    : '#2D2E30',
            }}
          >
            {info.getValue() ? (
              <Truncate
                content={info.getValue()}
                tooltipContent={info.getValue()}
              />
            ) : (
              '-'
            )}
          </span>
        );
      },
    },
    {
      Header: 'Created Date',
      accessor: 'created_on',
      filterVariant: 'datetime',
      customStyle: {
        minWidth: '0.1rem',
      },
    },
    {
      Header: 'Start Time',
      accessor: 'start_time',
      filterVariant: 'datetime',
      enableSorting: true,
      enableColumnFilter: true,
      customStyle: {
        minWidth: '0.1rem',
      },
    },
    {
      Header: 'End Time',
      accessor: 'estimated_end_time',
      filterVariant: 'datetime',
      enableSorting: true,
      enableColumnFilter: true,
      customStyle: {
        minWidth: '0.1rem',
      },
    },
    {
      Header: 'Total Distance',
      accessor: 'total_distance',
      enableSorting: true,
      enableColumnFilter: true,
      customStyle: {
        minWidth: '0.1rem',
      },
      cell: (info: any) => {
        return (
          <span
            style={{
              color:
                info.row?.original?.not_yet === true
                  ? Colors.Gray5
                  : theme === 'dark'
                    ? '#ececef'
                    : '#2D2E30',
            }}
          >
            {info.getValue() ? (
              <Truncate
                content={info.getValue()}
                tooltipContent={info.getValue()}
              />
            ) : (
              '-'
            )}
          </span>
        );
      },
    },
    {
      Header: 'Estimated Time',
      accessor: 'estimated_time',
      enableSorting: true,
      enableColumnFilter: true,
      customStyle: {
        minWidth: '0.1rem',
      },
      cell: (info: any) => {
        return (
          <span
            style={{
              color:
                info.row?.original?.not_yet === true
                  ? Colors.Gray5
                  : theme === 'dark'
                    ? '#ececef'
                    : '#2D2E30',
            }}
          >
            {info.getValue() ? (
              <Truncate
                content={info.getValue()}
                tooltipContent={info.getValue()}
              />
            ) : (
              '-'
            )}
          </span>
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
      Header: 'Operator',
      accessor: 'operator_full_name',
      enableSorting: true,
      enableColumnFilter: true,
      customStyle: {
        minWidth: '0.1rem',
      },
      cell: (info: any) => {
        return (
          <span
            style={{
              color:
                info.row?.original?.not_yet === true
                  ? Colors.Gray5
                  : theme === 'dark'
                    ? '#ececef'
                    : '#2D2E30',
            }}
          >
            {info.getValue() ? (
              <Truncate
                content={info.getValue()}
                tooltipContent={info.getValue()}
              />
            ) : (
              '-'
            )}
          </span>
        );
      },
    },
  ];

  //click row call api fetch detail profile
  const handleViewOrderDetail = useCallback(
    async (row: any) => {
      setIsStopRepeatProfile(
        row?.repeat_type__code && row?.repeat_type__code !== 'none'
          ? false
          : true,
      );
      if (row?.not_yet === false) {
        setSelectedRowForDetail(row);
        await fetchDetailSurveillanceProfile(row?.id as number);
        setRefreshChecklist(true);
      }
    },
    [
      setSelectedRowForDetail,
      fetchDetailSurveillanceProfile,
      selectedRowForDetail,
    ],
  );

  const { showLoading, hideLoading } = useLoadingContext();
  const handleGetListProfile = useCallback(
    async () => {
      showLoading();
      const { success, data, message } = await getListSurveillanceProfileAPI({
        pageSize,
        currentPage,
        objSearch,
        status__code: 'pending_device_check',
      });
      if (success) {
        const firstItemNotYet = data?.data?.find(
          (item: any) => item?.not_yet !== true,
        );
        setData(data);
        if (firstItemNotYet) {
          setSelectedRowForDetail(firstItemNotYet);
          setIsStopRepeatProfile(
            firstItemNotYet?.repeat_type__code &&
              firstItemNotYet?.repeat_type__code !== 'none'
              ? false
              : true,
          );
          await fetchDetailSurveillanceProfile(firstItemNotYet?.id as number);
        }
      }
      hideLoading();
    },
    [getListSurveillanceProfileAPI, pageSize, currentPage, objSearch], // eslint-disable-line react-hooks/exhaustive-deps
  );

  useEffect(() => {
    if (pageSize) {
      handleGetListProfile();
    }
  }, [pageSize, currentPage, objSearch]); // eslint-disable-line react-hooks/exhaustive-deps

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
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Select Drone section */}
          <Box
            flex={1}
            bgcolor={theme === 'dark' ? '#1F1F20' : '#FFFFFF'}
            borderRadius={3}
            p={'1rem'}
            height={480}
          >
            <CheckList
              setRefetchChecklist={setRefreshChecklist}
              setOpenModalStopRepeat={setOpenModalStopRepeat}
              isStopRepeatProfile={isStopRepeatProfile}
              refreshTable={refreshTable}
              setRefreshTable={setRefreshTable}
              selectedRowForDetail={detailSurveillanceProfile ?? null}
              handleRefreshWhenWaiting={async (profileId?: number) => {
                setData((prevData) => {
                  const filteredData = prevData.data.map((item: any) =>
                    item.id === profileId ? { ...item, not_yet: true } : item,
                  );
                  const firstItemNotYet = filteredData.find(
                    (item: any) => item?.not_yet !== true,
                  );
                  setTimeout(() => {
                    setSelectedRowForDetail(firstItemNotYet || null);
                    if (firstItemNotYet?.id) {
                      fetchDetailSurveillanceProfile(firstItemNotYet.id);
                    } else {
                      setDetailSurveillanceProfile(null);
                    }
                  }, 0);
                  return {
                    ...prevData,
                    data: filteredData,
                  };
                });
              }}
              handleRefreshDroneList={async (profileId?: number) => {
                const selectedRowForDetail = data.data.find(
                  (item) => item.id !== profileId,
                );
                if (selectedRowForDetail?.id) {
                  await fetchDetailSurveillanceProfile(selectedRowForDetail.id);
                }
              }}
              cancelDataProfile={(id) => {
                setData((prevData) => {
                  const filteredData = prevData.data.filter(
                    (item: any) => item.id !== id,
                  );
                  const firstItemNotYet = filteredData.find(
                    (item: any) => item?.not_yet !== true,
                  );
                  setTimeout(() => {
                    setSelectedRowForDetail(firstItemNotYet || null);
                    if (firstItemNotYet?.id) {
                      fetchDetailSurveillanceProfile(firstItemNotYet.id);
                    } else {
                      setDetailSurveillanceProfile(null);
                    }
                  }, 0);
                  return {
                    ...prevData,
                    data: filteredData,
                  };
                });
              }}
            />
          </Box>
        </Box>
        <CustomizableTable
          subTable
          notUseGroupColumn
          notShowSelectRow
          useSystemSetting
          availableHeight={spaceTableHeight}
          columns={COLUMNS}
          data={data}
          objSearch={objSearch}
          setObjSearch={setObjSearch}
          onClickRow={handleViewOrderDetail}
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
          hightlidhtRow={data.data?.find(
            (item) => item.id === selectedRowForDetail?.id,
          )}
        />
        <ProfileDetailModal
          show={openModalDetailProfile.show}
          onHide={() =>
            setOpenModalDetailProfile({ id: undefined, show: false })
          }
          detailData={detailSurveillanceProfile}
          markerData={markerData}
          droneRoutes={droneRoutes}
        />
        <CustomModal
          title={t('Stop Repeating Profile')}
          show={openModalStopRepeat.show}
          onHide={() => setOpenModalStopRepeat({ id: undefined, show: false })}
        >
          <div style={{ width: '25rem' }}>
            {t(
              'Do you want to stop this profile from repeating? If you confirm, no new profiles will be generated after this one is completed.',
            )}
          </div>
          <ActionBtn
            leftButtons={[
              <CustomBtn
                key="modal-save-btn"
                type="submit"
                color="primary"
                size="lg"
                actionType={ROLE_PERMISSION.UPDATE}
                label={t('Confirm')}
                loading={loadingStopRepeat}
                onClick={() =>
                  handleStopRepeatProfile(openModalStopRepeat.id as number)
                }
              />,
            ]}
            rightButtons={[
              <CustomBtn
                key="modal-cancel-btn"
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                loading={loadingStopRepeat}
                onClick={() =>
                  setOpenModalStopRepeat({ id: undefined, show: false })
                }
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>
      </Main>
    </Container>
  );
}
