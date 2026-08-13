// import { remToPx } from "@/utils/utils";
import { Box, Skeleton } from '@mui/material';
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import { CustomizableTable, useCalculateHeight, useTheme } from 'rj-core';

import API, { endpoint } from '@/services/API';
import { remToPx } from '@/utils/utils';

import { useOperationOrder } from '../../../hooks/useOperationOrder';
import { SearchParams } from '../ReadyToShipTab/types';
import OrderDetailModal from '../components/OrderDetailModal';
import DroneMonitoring from './DroneMonitoring';

// Types
interface OrderRow {
  id: number;
  order_id: string;
  current_status__code: string;
  order_time: string;
  sender: string;
  recipient: string;
  creator: string;
  number_of_package: number;
  origin: string;
  destination: string;
  estimated_distance?: string;
  estimated_duration?: string;
  route_options?: {
    id: number;
    name: string;
    distance: string;
    duration: string;
    is_recommended: boolean;
    stops: { name: string; note?: string }[];
  }[];
}

interface TableData {
  data: OrderRow[];
  totalItem: number;
  totalPage: number;
}

interface SelectTransitTabProps {
  selectedOrderFromPrevTab?: any;
}

export default function SelectTransitTab({
  selectedOrderFromPrevTab,
}: SelectTransitTabProps) {
  const [selectedOrder, setSelectedOrder] = useState<OrderRow | null>(null);
  const [theme] = useTheme();
  const { t } = useTranslation();
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [objSearch, setObjSearch] = useState<Record<string, unknown>>({});
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [data, setData] = useState<TableData>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedRowForDetail, setSelectedRowForDetail] =
    useState<OrderRow | null>(null);
  const headerPageRef = React.useRef<HTMLDivElement>(null);
  const selectedOrderPanelRef = useRef<HTMLDivElement>(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(8), 420],
  });

  const { fetchTransitOrder } = useOperationOrder();

  const fetchOrderDetail = async (orderId: string) => {
    const { success, data } = await API.get(endpoint.detailOrder(orderId));
    if (success) {
      setSelectedRowForDetail(data);
    }
  };

  const COLUMNS = [
    { Header: 'Order ID', accessor: 'order__order_code' },
    {
      Header: 'Order Time',
      accessor: 'order__created_on',
      filterVariant: 'datetime',
    },
    { Header: 'Origin', accessor: 'origin' },
    { Header: 'Destination', accessor: 'destination' },
    {
      Header: 'Drone Name',
      accessor: 'device_name',
      cell: (row) =>
        Array.isArray(row?.getValue()) && row?.getValue()?.join(', '),
    },
    { Header: 'Route', accessor: 'route' },
    { Header: 'Sender', accessor: 'order__sender_name' },
    { Header: 'Recipient', accessor: 'order__recipient_name' },
    {
      Header: 'Number of Package',
      accessor: 'number_of_packages',
    },
    {
      Header: t(' '),
      accessor: 'action',
      cell: (row: { row: { original: OrderRow } }) => (
        <div
          className="special-label"
          onClick={(e) => {
            e.stopPropagation();
            fetchOrderDetail(row.row.original.order_id);
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

  const handleGetOrders = async ({
    pageSize,
    currentPage,
    objSearch,
  }: SearchParams) => {
    const objSearchFetch = {
      ...objSearch,
      status_codes: ['in_transit_processing'],
    };
    const response = await fetchTransitOrder({
      pageSize,
      currentPage,
      objSearch: objSearchFetch,
    });
    if (response) {
      setData({
        data: response.data,
        totalPage: response.totalPage,
        totalItem: response.totalItem,
      });
      if (response?.data?.length > 0) {
        setSelectedOrder(response?.data?.[0]);
      }
    }
  };

  // Handle row click for table
  const handleViewOrderDetail = async (row: OrderRow) => {
    setSelectedOrder(row);
  };

  useEffect(() => {
    if (pageSize) {
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
    }
  }, [pageSize, currentPage, objSearch]);

  // Auto-select order from previous tab (one-time, no retry)
  useEffect(() => {
    if (selectedOrderFromPrevTab && data.data.length > 0) {
      // Find the order in the current data by order_id
      const matchingOrder = data.data.find(
        (item) => item.order_id === selectedOrderFromPrevTab.order__id,
      );

      if (matchingOrder) {
        console.log('✅ Found matching order in In Transit:', matchingOrder);
        handleViewOrderDetail(matchingOrder);
      }
    }
  }, [selectedOrderFromPrevTab, data.data]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Box>
      <div ref={headerPageRef} />
      {selectedOrder ? (
        <div ref={selectedOrderPanelRef}>
          <DroneMonitoring selectedOrder={selectedOrder} />
        </div>
      ) : (
        <Box
          ref={selectedOrderPanelRef}
          display="flex"
          gap={2}
          mb={2}
        >
          {/* Map Skeleton */}
          <Box flex={1}>
            <Skeleton
              variant="rectangular"
              height={400}
              sx={{
                borderRadius: 2,
                bgcolor: theme === 'dark' ? '#1F1F20' : 'rgba(0, 0, 0, 0.08)',
              }}
              animation="wave"
            />
          </Box>
          {/* Route Selection Skeleton */}
          <Box flex={1}>
            <Skeleton
              variant="rectangular"
              height={400}
              sx={{
                borderRadius: 2,
                bgcolor: theme === 'dark' ? '#1F1F20' : 'rgba(0, 0, 0, 0.08)',
              }}
              animation="wave"
            />
          </Box>
        </Box>
      )}
      <CustomizableTable
        subTable
        useSystemSetting
        notShowSelectRow
        columns={COLUMNS}
        data={data}
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
        hightlidhtRow={data.data?.find((item) => item.id === selectedOrder?.id)}
      />
      <OrderDetailModal
        show={isDetailModalOpen}
        onHide={() => setIsDetailModalOpen(false)}
        detailData={selectedRowForDetail}
      />
    </Box>
  );
}
