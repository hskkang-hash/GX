import { Box } from '@mui/material';
import { t } from 'i18next';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { GoPlus } from 'react-icons/go';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBtn,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import ErrorImage from '@/assets/images/no-image.png';
import SwitchBtn from '@/components/Form/SwitchBtn';
import { CustomRoutes } from '@/services/API';
import { isEmptyObject, remToPx } from '@/utils/utils';

import useCommonAPI from '../useCommonAPI/useAPI';
import useDockingStation from './hooks/useDockingStation';
import useAPI from '../terminals/useAPI/useAPI';
import OperatingTimeModal from '../terminals/components/OperatingTimeModal';

const DockingStationImage = React.memo<{
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

DockingStationImage.displayName = 'DockingStationImage';

interface DockingStationState {
  id: string;
  code: string;
  avatar_id?: string;
  avatar__file_url?: string;
  name: string;
  active?: boolean;
  created_on?: string;
  terminal_base_type: string;
  full_address: string;
  address?: string;
  latitude: number;
  longitude: number;
  postal_code?: number | null | undefined;
  url?: string;
  manager?: string;
  manager_name?: string;
  note?: string;
  // docking_station_type__name?: string;
  terminal_type_ids?: string | number | null;
  function_ids?: string | number | null;
  temp_function_ids?: string | number | null;
  time_stops: {
    value: number | null;
    unit: string;
  };
}

// Type for table row
interface TableRow {
  row: {
    original: DockingStationState;
  };
}

const DockingStation = () => {
  const [objSearch, setObjSearch] = useState({});
  const navigate = useNavigate();
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const {
    getDockingStationList,
    changeStatusDockingStation,
    activeDockingStationAPI,
    deactiveDockingStationAPI,
  } = useDockingStation();

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  const fetchDockingStationList = async () => {
    const { success, message, data, total_items, total_pages } =
      await getDockingStationList({
        pageSize,
        currentPage,
        objSearch,
      });
    if (success) {
      setData({
        data: data,
        totalItem: total_items,
        totalPage: total_pages,
      });
    } else {
      ToastTopHelper.error(message);
    }
  };

  useEffect(() => {
    if (pageSize && !isEmptyObject(objSearch)) {
      fetchDockingStationList();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageSize, currentPage, objSearch]);

  const handleSelectionRows = (selectedData: any[]) => {
    setSelectedRows(selectedData);
  };

  const handleActionDockingStation = useCallback(
    async (action: 'activate' | 'deactivate', info?: any) => {
      setLoadingDockingId(info?.id);
      const listId =
        selectedRows?.map((item: any) => item.id).join(',') || String(info?.id);
      const { success, message } = await (
        action === 'activate'
          ? activeDockingStationAPI
          : deactiveDockingStationAPI
      )({
        ids: listId,
        useLoading: true,
      });
      if (success) {
        const updatedData = data?.data?.map((item) => {
          const found = selectedRows?.find((row: any) => row?.id === item?.id);
          const isTargetItem = info && item?.id === info?.id;
          if (found || isTargetItem) {
            return {
              ...item,
              active: action === 'activate' ? true : false,
            };
          }
          return item;
        });
        setData((prevData) => ({
          ...prevData,
          data: updatedData,
        }));
        setRefreshTable(true);
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
      setLoadingDockingId(null);
    },
    [selectedRows, activeDockingStationAPI, deactiveDockingStationAPI], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const [loadingDockingId, setLoadingDockingId] = useState<string | null>(null);

  const handleViewDetailDockingStation = (selectedRow: any) => {
    if (selectedRow?.active && selectedRow?.id) {
      navigate(
        CustomRoutes.dockingStation.subRoutes.detailDockingStation.path.replace(
          ':id',
          selectedRow.id.toString(),
        ),
      );
    }
  };

  const headerPageRef = useRef(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  const handleregister = () => {
    navigate(CustomRoutes.dockingStation.subRoutes.register.path);
  };

  const ImageCell = useMemo(
    () =>
      ({ info }: { info: any }) => {
        return (
          <DockingStationImage
            imageUrl={info?.row?.original?.avatar__file_url || ErrorImage}
            alt="docking station"
          />
        );
      },
    [],
  );

  const { getFunctionTypes, useFetchOptions } = useCommonAPI();
  const mainTypeConfig = useMemo(
    () => ({
      type: 'function' as const,
      params: { function_type: 'docking_station' },
      defaultLabel: t('Select'),
    }),
    [],
  );
  const mainType = useFetchOptions(getFunctionTypes, mainTypeConfig);
  const {
    getOperatingTimeTerminalAPI,
  } = useAPI();


  const [showDetailModal, setShowDetailModal] = useState<{ show: boolean, data: any }>({
    show: false,
    data: {},
  });


  const handleViewOperatingTime = async (id: number) => {
    const { success, message, data } = await getOperatingTimeTerminalAPI(id);
    console.log('data_operating_time', data);
    if (success) {
      setShowDetailModal({ show: true, data: data });
    } else {
      ToastTopHelper.error(message);
    }

  };

  // Memoized columns to prevent unnecessary re-renders
  const columnsOther = [
    {
      Header: 'Image',
      accessor: 'image',
      enableSorting: false,
      enableColumnFilter: false,
      cell: (info: any) => <ImageCell info={info} />,
      width: 120,
      minWidth: 120,
      maxWidth: 120,
    },
    {
      Header: t('Type'),
      accessor: 'function',
      filterVariant: 'select',
      filterOptions:
        mainType.length > 0
          ? mainType?.map((item: any) => ({
            label: item.label,
            value:
              item.label == 'Select' ||
                item.label == '선택' ||
                item.label == 'เลือก'
                ? ''
                : item.label,
          }))
          : [],
      cell: (row: any) => {
        return <>{row.getValue() || '-'}</>;
      },
    },
    {
      Header: 'Operating Time',
      accessor: 'operating_times',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: { maxWidth: 120, textAlign: 'center' },
      notUseConfigTable: true,
      cell: (info: any) => {
        return (
          <>
            <CustomBtn
              label={t('View Detail')}
              variant="outline"
              style={{ border: '1px solid #1d9be2', color: '#1d9be2' }}
              actionType={ROLE_PERMISSION.CREATE}
              onClick={() =>
                handleViewOperatingTime(info?.row?.original?.id)
              }
            />
          </>
        );
      },
    },
  ];

  const StatusCell = useCallback(
    ({ info }: { info: any }) => {
      return (
        <SwitchBtn
          actionType={ROLE_PERMISSION.UPDATE}
          statusValue={info?.row?.original?.active}
          onChange={() => {
            setSelectedRows([info?.row?.original]);
            handleActionDockingStation(
              info?.row?.original?.active
                ? 'deactivate'
                : ('activate' as 'activate' | 'deactivate'),
              info?.row?.original,
            );
          }}
          loading={
            loadingDockingId
              ? loadingDockingId === info?.row?.original?.id
              : false
          }
        />
      );
    },
    [handleActionDockingStation, loadingDockingId],
  );

  const columnsActive = useMemo(() => {
    return [
      {
        Header: t('Active'),
        accessor: 'active',
        enableSorting: true,
        enableColumnFilter: false,
        cell: (info: any) => <StatusCell info={info} />,
      },
    ];
  }, [t, StatusCell]);

  return (
    <Container
      id="list-docking-station"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Register')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={handleregister}
          />,
        ]}
      />

      <Main>
        <div className="list-docking-station__table-container">
          <CustomizableTable
            stickyHeader
            availableHeight={spaceTableHeight}
            columns={[...columnsActive, ...columnsOther] as never}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleViewDetailDockingStation}
            onSelectedRows={handleSelectionRows}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            buttons={[
              <CustomBtn
                label={t('Activate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionDockingStation('activate')}
              />,
              <CustomBtn
                label={t('Deactivate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionDockingStation('deactivate')}
              />,
            ]}
            pageSize={pageSize}
            setPageSize={setPageSize}
            offcanvas={openOffcanvas}
            setOpenOffcanvas={(boolean: boolean) => {
              setOpenOffcanvas(boolean);
            }}
          />
        </div>
      </Main>
      <OperatingTimeModal
        show={showDetailModal.show}
        onHide={() => setShowDetailModal({ show: false, data: {} })}
        data={showDetailModal.data} />
    </Container>
  );
};
export default DockingStation;
