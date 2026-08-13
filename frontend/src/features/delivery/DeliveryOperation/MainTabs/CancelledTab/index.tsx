import { Box } from '@mui/material';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { CustomizableTable, useCalculateHeight } from 'rj-core';

import { CustomRoutes } from '@/services/API';
import { getContrastTextColor, remToPx } from '@/utils/utils';

import { formatStatusDeliveryInquiry } from '../../../deliveryInquiry/utils/StatusColorInquiry';
import { useOperationOrder } from '../../hooks/useOperationOrder';

const columns = [
  { Header: 'Order ID', accessor: 'order_id' },
  { Header: 'Order Time', accessor: 'order_time' },
  { Header: 'Order Cancellation Time', accessor: 'order_cancellation_time' },
  // { Header: 'Reason', accessor: 'reason' },
  // { Header: 'Cancelled By', accessor: 'cancelled_by' },
  // { Header: 'Refund Time', accessor: 'refund_time' },
  { Header: 'Sender', accessor: 'sender' },
  { Header: 'Recipient', accessor: 'recipient' },
  { Header: 'Creator', accessor: 'creator' },
  {
    Header: 'Number of Package',
    accessor: 'number_of_packages',
  },
  {
    Header: 'Mapped Status',
    accessor: 'mapped_status',
    enableColumnFilter: false,
    cell: (info) => {
      console.log('info', info.row.original);
      const { t } = useTranslation();
      const mappedListStatus = info.row.original?.mapped_status_list;

      const mappedStatusCode = info.row.original?.mapped_status_code;
      const currentStatusName = info.row.original?.mapped_status;
      const currentTextColor = getContrastTextColor(
        info.row.original?.mapped_status_background_color,
      );
      const currentBackgroundColor =
        info.row.original?.mapped_status_background_color;
      const currentBorderColor = info.row.original?.mapped_status_border_color;

      return (
        <div
          style={{
            display: 'flex',
            gap: 8,
            width: 'fit-content',
            flexFlow: 'wrap',
          }}
        >
          {mappedListStatus?.length > 0
            ? mappedListStatus?.map(
              (item: {
                name: string;
                code: string;
                background_color: string;
                text_color: string;
                border_color: string;
              }) =>
                formatStatusDeliveryInquiry({
                  t,
                  status_name: item.name,
                  status_code: mappedStatusCode,
                  backgroundColor: item.background_color,
                  color: item.text_color,
                  border: item.border_color,
                  isShowButton: false,
                }),
            )
            : mappedStatusCode &&
            formatStatusDeliveryInquiry({
              t,
              status_name: currentStatusName,
              status_code: mappedStatusCode,
              backgroundColor: currentBackgroundColor,
              color: currentTextColor,
              border: currentBorderColor,
              isShowButton: false,
            })}
        </div>
      );
    },
  },
];

interface TableRow {
  order_id: string;
  order_time: string;
  order_cancellation_time: string;
  reason: string;
  cancelled_by: string;
  refund_time: string;
  sender: string;
  recipient: string;
  creator: string;
  number_of_package: number;
}

export default function CancelledTab() {
  const [selectedRows, setSelectedRows] = useState([]);
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [objSearch, setObjSearch] = useState({});
  const [cancelledOrders, setCancelledOrders] = useState([]);

  const { fetchOperationOrder } = useOperationOrder();

  const headerPageRef = useRef(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4)],
  });

  const handleViewOrderDetail = (row) => {
    if (row.order_id) {
      navigate(
        CustomRoutes.deliveryOperation.subRoutes.orderDetail.path.replace(
          ':id',
          row.id.toString(),
        ) +
        '?orderId=' +
        row.order_id,
      );
    }
  };

  const handleGetCancelledOrders = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch: any;
  }) => {
    const objSearchFetch = {
      ...objSearch,
      status_codes: 'cancelled',
    };
    const { data, totalPage, totalItem } = await fetchOperationOrder({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearchFetch,
    });

    setCancelledOrders({
      data: data,
      totalPage: totalPage,
      totalItem: totalItem,
    });
  };

  useEffect(() => {
    if (pageSize) {
      handleGetCancelledOrders({
        pageSize: pageSize,
        currentPage: currentPage,
        objSearch: objSearch,
      });
    }
  }, [pageSize, currentPage, objSearch]);

  return (
    <Box px="1rem">
      <CustomizableTable
        columns={columns}
        data={cancelledOrders}
        refreshTable={refreshTable}
        setRefreshTable={setRefreshTable}
        onSelectedRows={setSelectedRows}
        objSearch={objSearch}
        setObjSearch={setObjSearch}
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        pageSize={pageSize}
        setPageSize={setPageSize}
        stickyHeader
        availableHeight={spaceTableHeight}
        onClickRow={handleViewOrderDetail}
      />
    </Box>
  );
}
