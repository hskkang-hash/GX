import { useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';

import { formatStatusDeliveryInquiry } from '@/features/delivery/deliveryInquiry/utils/StatusColorInquiry';

import { OrderRow } from '../types';

interface UseOptimizedTableDataProps {
  data: {
    data: OrderRow[];
    totalItem: number;
    totalPage: number;
  };
  highlightedOrders: number[];
  currentOrderDetails: OrderRow | null;
  onViewOrderDetail: (orderId: number) => void;
  onSetDetailModalOpen: (open: boolean) => void;
  onSetDataDetailOrder: (data: any) => void;
}

export const useOptimizedTableData = ({
  data,
  highlightedOrders,
  currentOrderDetails,
  onViewOrderDetail,
  onSetDetailModalOpen,
  onSetDataDetailOrder,
}: UseOptimizedTableDataProps) => {
  const { t } = useTranslation();

  // Memoized table columns - using function definitions instead of JSX
  const columns = useMemo(
    () => [
      { Header: 'Order ID', accessor: 'order_id' },
      { Header: 'Order Time', accessor: 'order_time' },
      { Header: 'Sender', accessor: 'sender' },
      { Header: 'Recipient', accessor: 'recipient' },
      { Header: 'Creator', accessor: 'creator' },
      { Header: 'Number of Package', accessor: 'number_of_package' },
      {
        Header: 'Mapped Status',
        accessor: 'mapped_status',
        enableColumnFilter: false,
        cell: (info: any) => {
          const mappedListStatus = info.row.original?.mapped_status_list;
          return {
            type: 'mapped_status',
            data:
              mappedListStatus?.map((item: any) =>
                formatStatusDeliveryInquiry({
                  t,
                  status_name: item.name,
                  status_code: item.code,
                  backgroundColor: item.background_color,
                  color: item.text_color,
                  border: item.border_color,
                }),
              ) || [],
          };
        },
      },
      {
        Header: t(' '),
        accessor: 'action',
        cell: (row: any) => ({
          type: 'action_button',
          onClick: (e: any) => {
            e.stopPropagation();
            onSetDataDetailOrder(null);
            onViewOrderDetail(row?.row?.original.order__id);
            onSetDetailModalOpen(true);
          },
        }),
        customStyle: { maxWidth: 20, textAlign: 'center' },
        enableSorting: false,
        notUseConfigTable: true,
      },
    ],
    [t, onSetDataDetailOrder, onViewOrderDetail, onSetDetailModalOpen],
  );

  // Memoized table data with highlights
  const enhancedTableData = useMemo(
    () => ({
      ...data,
      data: data.data.map((order) => ({
        ...order,
        isHighlighted: highlightedOrders.includes(order.id),
      })),
    }),
    [data, highlightedOrders],
  );

  // Memoized search params for ready to ship orders
  const searchParams = useMemo(
    () => ({
      status_codes: ['select_route_processing'],
    }),
    [],
  );

  // Memoized highlighted order IDs for cross-order functionality
  const highlightedOrderIds = useMemo(() => {
    if (!currentOrderDetails || !data.data.length) return [];

    return data.data
      .filter(
        (order) =>
          order.id !== currentOrderDetails.id &&
          order.origin === currentOrderDetails.origin &&
          order.destination === currentOrderDetails.destination,
      )
      .map((order) => order.id);
  }, [currentOrderDetails, data.data]);

  // Optimized row click handler
  const handleRowClick = useCallback((row: OrderRow) => {
    // This will be handled by the parent component
    return row;
  }, []);

  // Format status function for external use
  const formatStatus = useCallback(
    (mappedListStatus: any[]) => {
      return (
        mappedListStatus?.map((item: any) =>
          formatStatusDeliveryInquiry({
            t,
            status_name: item.name,
            status_code: item.code,
            backgroundColor: item.background_color,
            color: item.text_color,
            border: item.border_color,
          }),
        ) || []
      );
    },
    [t],
  );

  return {
    columns,
    enhancedTableData,
    searchParams,
    highlightedOrderIds,
    handleRowClick,
    formatStatus,
  };
};
