import { Box } from '@mui/material';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import {
  CustomBtn,
  CustomizableTable,
  useCalculateHeight,
  useLoadingContext,
  useTheme,
} from 'rj-core';

import useChecklistSetting from '@/features/checklistSetting/hooks/useChecklistSetting';
import { remToPx } from '@/utils/utils';

import { useOperationOrder } from '../../../hooks/useOperationOrder';
import { convertDataForChecklist } from '../../../utils/convertDataForChecklist';
import { CheckList } from '../components/CheckList';
import { DroneSensorStatusType } from '../components/DroneSensorStatus';
import OrderDetailModalV2 from '../components/OrderDetailModalV2';

interface TableData {
  data: any[];
  totalItem: number;
  totalPage: number;
}

interface ChecklistSetting {
  name_category: string;
  item: {
    id: string;
    item_name: string;
  }[];
}

interface DeviceCheckTabProps {
  selectedOrderFromPrevTab?: any;
  onNavigateToInTransit?: (tabIndex: number, orderData?: any) => void;
}

export default function DeviceCheckTab({
  selectedOrderFromPrevTab,
  onNavigateToInTransit,
}: DeviceCheckTabProps) {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const { getChecklistSetting } = useChecklistSetting();
  const { fetchOperationOrder, actionDeliveryStart } = useOperationOrder();
  const headerPageRef = useRef<HTMLDivElement>(null);

  const [data, setData] = useState<TableData>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  const [droneSensorStatus, setDroneSensorStatus] = useState<
    DroneSensorStatusType[]
  >([]);
  const [sensorStatus, setSensorStatus] = useState<any>({});
  const [checklistSetting, setChecklistSetting] = useState<ChecklistSetting[]>(
    [],
  );

  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [refreshChecklist, setRefreshChecklist] = useState<boolean>(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [objSearch, setObjSearch] = useState<Record<string, unknown>>({});
  const [selectedRowForDetail, setSelectedRowForDetail] = useState<any | null>(
    null,
  );
  const [ordersForDetail, setOrdersForDetail] = useState({
    order_ids: [],
    order_codes: [],
    drone_id: null,
    drone_unique_id: null,
    disable_row: false,
    selected_checklist: [],
  });
  const [orderIdsForDetail, setOrderIdsForDetail] = useState<number[]>([]);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4), remToPx(1), 400],
  });

  const handleDeliveryStart = async (row: any) => {
    const response = await actionDeliveryStart({
      order_ids: row.order_ids,
      drone_id: row.id,
    });
    if (response?.success) {
      setOrdersForDetail({
        order_ids: [],
        order_codes: [],
        drone_id: null,
        drone_unique_id: null,
        disable_row: false,
        selected_checklist: [],
      });
      handleGetOrders();

      // Navigate to In Transit tab after successful delivery start
      if (onNavigateToInTransit && row) {
        console.log(
          '✅ Delivery started, navigating to In Transit tab with order:',
          row,
        );
        onNavigateToInTransit(2, row);
      }
    }
  };

  const COLUMNS = [
    { Header: t('Drone Name'), accessor: 'drone__name' },
    { Header: 'Drone ID', accessor: 'drone__unit_id' },
    {
      Header: 'Route',
      accessor: 'route_names',
      cell: (row) => row?.getValue()?.join(', '),
    },
    {
      Header: 'Order ID',
      accessor: 'order_codes',
      cell: (row) => row?.getValue()?.join(', '),
    },
    {
      Header: 'Origin',
      accessor: 'origin',
      cell: (row) => row?.getValue()?.join(', '),
    },
    {
      Header: 'Destination',
      accessor: 'destination',
      cell: (row) => <>{row?.getValue()?.join(', ')}</>,
    },
    { Header: 'Number of Package', accessor: 'number_of_packages' },
    {
      Header: t(' '),
      accessor: 'action1',
      cell: (row: any) => {
        return (
          <div
            style={{ width: '100%', display: 'flex', justifyContent: 'center' }}
          >
            {row?.row?.original?.delivery_start_display ? (
              <CustomBtn
                label={t('Delivery Start')}
                variant="outline"
                color="primary"
                size="sm"
                disabled={!row?.row?.original?.delivery_start_active}
                // onClick={() => handleToggleTerminal(terminal)}
                onClick={() => handleDeliveryStart(row?.row?.original)}
              />
            ) : (
              <></>
            )}
          </div>
        );
      },
      customStyle: {
        maxWidth: 120,
        textAlign: 'center',
      },
      enableSorting: false,
      enableColumnFilter: false,
      notUseConfigTable: true,
    },
    {
      Header: t(' '),
      accessor: 'action',
      cell: (row: any) => (
        <div
          className="special-label"
          style={{ cursor: 'pointer' }}
          onClick={(e) => {
            e.stopPropagation();
            setOrderIdsForDetail(row?.row?.original.order_ids);
            setIsDetailModalOpen(true);
          }}
        >
          <BsEye size={16} />
        </div>
      ),
      customStyle: { maxWidth: 20, textAlign: 'center' },
      enableSorting: false,
      enableColumnFilter: false,
      notUseConfigTable: true,
    },
  ] as const;

  // View order detail
  const handleViewOrderDetail = async (row: any) => {
    setDroneSensorStatus([]);
    setSelectedRowForDetail(row);
    setOrdersForDetail({
      order_ids: row.order_ids,
      order_codes: row.order_codes,
      drone_id: row.id,
      drone_unique_id: row.unit_id,
      disable_row: row.disable_row,
      selected_checklist: row.checklist_items,
    });
    handleGetChecklistSetting(row.unit_id);
    setRefreshChecklist(true);
  };

  // Get list orders
  const handleGetOrders = useCallback(
    async () => {
      const objSearchFetch = {
        ...objSearch,
        status_codes: ['select_drone_processing'],
      };
      const response = await fetchOperationOrder({
        pageSize: pageSize ?? 25,
        currentPage,
        objSearch: objSearchFetch,
      });
      if (response) {
        const mappedData = response.data.map((item) => ({
          ...item,
        }));
        setData({
          data: mappedData,
          totalPage: response.totalPage,
          totalItem: response.totalItem,
        });
        if (response && mappedData.length > 0) {
          handleGetChecklistSetting(mappedData[0].unit_id);
          setSelectedRowForDetail(mappedData[0]);
          setOrdersForDetail({
            order_ids: mappedData[0].order_ids,
            order_codes: mappedData[0].order_codes,
            drone_id: mappedData[0].id,
            drone_unique_id: mappedData[0].unit_id,
            disable_row: mappedData[0].disable_row,
            selected_checklist: mappedData[0].checklist_items,
          });
        }
      }
    },
    [fetchOperationOrder, pageSize, currentPage, objSearch], // eslint-disable-line react-hooks/exhaustive-deps
  );

  // Get checklist setting
  const handleGetChecklistSetting = useCallback(
    async (deviceId: number | string) => {
      const { data: dataChecklistSetting, auto_checklist, sensorStatus } =
        await getChecklistSetting({
          currentPage: 1,
          pageSize: 10000,
          objSearch: {
            searchParams: [
              {
                id: 'device_id',
                value: deviceId,
              },
              {
                id: 'active',
                value: true,
              },
            ],
          },
        });

      setChecklistSetting(convertDataForChecklist(dataChecklistSetting));
      setDroneSensorStatus(auto_checklist || []);
      setSensorStatus(sensorStatus || {});
    },
    [getChecklistSetting, setChecklistSetting, setDroneSensorStatus],
  );

  const { showLoading, hideLoading } = useLoadingContext();
  const [loadingSensorStatus, setLoadingSensorStatus] = useState<boolean>(false);

  // Refresh only sensorStatus
  const handleRefreshSensorStatus = useCallback(async () => {
    if (ordersForDetail.drone_unique_id) {
      setLoadingSensorStatus(true);
      showLoading();
      try {
        const { sensorStatus } = await getChecklistSetting({
          currentPage: 1,
          pageSize: 10000,
          objSearch: {
            searchParams: [
              {
                id: 'device_id',
                value: ordersForDetail.drone_unique_id,
              },
              {
                id: 'active',
                value: true,
              },
            ],
          },
        });
        setSensorStatus(sensorStatus || {});
        setLoadingSensorStatus(false);
      } catch (error) {
        console.error('Error refreshing sensor status:', error);
      } finally {
        hideLoading();
        setLoadingSensorStatus(false);
      }
    }
  }, [getChecklistSetting, ordersForDetail.drone_unique_id]);

  // Get list orders
  useEffect(() => {
    if (pageSize) {
      handleGetOrders();
    }
  }, [pageSize, currentPage, objSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-select order from previous tab (one-time, no retry)
  useEffect(() => {
    if (selectedOrderFromPrevTab && data.data.length > 0) {
      // Find the order in the current data by order_id
      const matchingOrder = data.data.find(
        (item) =>
          item.order_ids &&
          item.order_ids.includes(selectedOrderFromPrevTab.order__id),
      );

      if (matchingOrder) {
        console.log('✅ Found matching order in Device Check:', matchingOrder);
        handleViewOrderDetail(matchingOrder);
      }
    }
  }, [selectedOrderFromPrevTab, data.data]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Box>
      <Box
        display="flex"
        gap={2}
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
            routeId={selectedRowForDetail?.route_id}
            checklistSetting={checklistSetting}
            sensorStatus={sensorStatus}
            loadingSensorStatus={loadingSensorStatus}
            droneSensorStatus={droneSensorStatus}
            orderIds={ordersForDetail.order_ids}
            droneId={ordersForDetail.drone_id}
            droneUniqueId={ordersForDetail.drone_unique_id}
            selectedChecklist={ordersForDetail?.selected_checklist}
            checklistDisabled={ordersForDetail?.disable_row}
            refetchChecklist={refreshChecklist}
            setDroneSensorStatus={setDroneSensorStatus}
            setRefetchChecklist={setRefreshChecklist}
            selectedRowForDetail={selectedRowForDetail}
            handleRefreshDroneList={() => {
              setOrdersForDetail({
                order_ids: [],
                order_codes: [],
                drone_id: null,
                drone_unique_id: null,
                disable_row: false,
                selected_checklist: [],
              });
              setSensorStatus({});
              handleGetOrders();
            }}
            onRefreshSensorStatus={handleRefreshSensorStatus}
            onNavigateToInTransit={onNavigateToInTransit}
            currentOrderData={selectedRowForDetail}
          />
        </Box>
      </Box>
      <CustomizableTable
        notShowSelectRow
        useSystemSetting={true}
        columns={COLUMNS}
        data={data}
        useSystemConfigTable={true}
        refreshTable={refreshTable}
        setRefreshTable={setRefreshTable}
        objSearch={objSearch}
        setObjSearch={setObjSearch}
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        pageSize={pageSize}
        setPageSize={setPageSize}
        stickyHeader
        availableHeight={spaceTableHeight}
        onClickRow={handleViewOrderDetail}
        hightlidhtRow={data.data?.find(
          (item) => item.id === selectedRowForDetail?.id,
        )}
      />
      <OrderDetailModalV2
        show={isDetailModalOpen}
        onHide={() => setIsDetailModalOpen(false)}
        hasTabs={true}
        orderIds={orderIdsForDetail}
      />
    </Box>
  );
}
