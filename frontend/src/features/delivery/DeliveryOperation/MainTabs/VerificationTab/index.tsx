import { Box } from '@mui/material';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  CustomBtn,
  CustomizableTable,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import CustomSelectControlled from '@/components/selects/CustomSelectControlled';
import { colorOpacity } from '@/configs/Colors';
import API, { CustomRoutes, endpoint } from '@/services/API';
import { getContrastTextColor, remToPx } from '@/utils/utils';

import { formatStatusDeliveryInquiry } from '../../../deliveryInquiry/utils/StatusColorInquiry';
import { useOperationOrder } from '../../hooks/useOperationOrder';

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
}

interface TableData {
  data: OrderRow[];
  totalItem: number;
  totalPage: number;
}

interface SearchParams {
  pageSize: number;
  currentPage: number;
  objSearch: Record<string, any>;
}

const COLUMNS = [
  { Header: 'Order ID', accessor: 'order_id' },
  { Header: 'Order Time', accessor: 'order_time' },
  { Header: 'Sender', accessor: 'sender' },
  { Header: 'Recipient', accessor: 'recipient' },
  { Header: 'Creator', accessor: 'creator' },
  { Header: 'Number of Package', accessor: 'number_of_package' },
  { Header: 'Created On', accessor: 'created_on', filterVariant: 'datetime' },
  {
    Header: 'Order Created On',
    accessor: 'order__created_on',
    filterVariant: 'datetime',
  },
  { Header: 'Created On', accessor: 'created_on', filterVariant: 'datetime' },
  {
    Header: 'Mapped Status',
    accessor: 'mapped_status',
    enableColumnFilter: false,
    cell: (info) => {
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
] as const;

export default function VerificationTab() {
  const [selectedTab, setSelectedTab] = useState<string[]>([
    'unverified_order',
    'verified_order',
  ]);
  const [showAction, setShowAction] = useState<Record<string, boolean>>({
    verify: false,
  });
  const [selectedRows, setSelectedRows] = useState<OrderRow[]>([]);
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [objSearch, setObjSearch] = useState<Record<string, any>>({});
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [data, setData] = useState<TableData>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  // Hooks
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { fetchOperationOrder } = useOperationOrder();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4)],
  });

  // Constants
  const TAB_OPTIONS = [
    { value: ['unverified_order', 'verified_order'], label: t('All') },
    { value: ['unverified_order'], label: t('Unverified Order') },
    { value: ['verified_order'], label: t('Verified Order') },
  ] as const;

  const handleViewOrderDetail = (row: OrderRow) => {
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

  const handleGetOrders = async ({
    pageSize,
    currentPage,
    objSearch,
  }: SearchParams) => {
    const objSearchFetch = {
      ...objSearch,
      status_codes: selectedTab,
    };
    console.log('objSearchFetch', objSearchFetch);

    const response = await fetchOperationOrder({
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
    }
  };

  const getActionButtons = () => {
    if (!selectedRows.length)
      return selectedTab === TAB_OPTIONS[1].value
        ? [
          <CustomBtn
            key="verify"
            label={t('Verify')}
            type="button"
            variant="outline"
            color="primary"
            size="sm"
            disabled={!selectedRows.length}
            onClick={handleVerifyOrder}
          />,
        ]
        : [];

    const allUnverified = selectedRows.every(
      (row) => row.current_status__code === 'unverified_order',
    );
    const allVerified = selectedRows.every(
      (row) => row.current_status__code === 'verified_order',
    );

    if (allUnverified) {
      return [
        <CustomBtn
          key="verify"
          label={t('Verify')}
          type="button"
          variant="outline"
          color="primary"
          size="sm"
          onClick={handleVerifyOrder}
        />,
      ];
    }

    return [];
  };

  const handleVerifyOrder = async () => {
    const formData = { operation_ids: selectedRows.map((row) => row.id) };
    const { success, message } = await API.post(endpoint.verifyOders, formData);

    if (success) {
      setRefreshTable(true);
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
      ToastTopHelper.success(message || t('Verified Success'));
    }
  };

  // Effects
  useEffect(() => {
    if (pageSize && selectedTab) {
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
    }
  }, [pageSize, currentPage, objSearch, selectedTab]);

  return (
    <Box px="1rem">
      <CustomizableTable
        columns={COLUMNS}
        data={data}
        refreshTable={refreshTable}
        setRefreshTable={setRefreshTable}
        objSearch={objSearch}
        setObjSearch={setObjSearch}
        onSelectedRows={setSelectedRows}
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        pageSize={pageSize}
        setPageSize={setPageSize}
        stickyHeader
        availableHeight={spaceTableHeight}
        buttons={getActionButtons()}
        buttonGroups={[
          {
            position: 'top',
            align: 'right',
            buttons: [
              <CustomSelectControlled
                key="tab-select"
                size="sm"
                options={TAB_OPTIONS}
                value={TAB_OPTIONS.find((opt) =>
                  Array.isArray(opt.value) && Array.isArray(selectedTab)
                    ? JSON.stringify(opt.value) === JSON.stringify(selectedTab)
                    : opt.value === selectedTab,
                )}
                setValue={(opt) => {
                  setSelectedTab(opt ? opt.value : []);
                  setRefreshTable(true);
                }}
                menuPlacement="auto"
                menuPortalTarget={document.body}
                disabled={false}
              />,
            ],
          },
        ]}
        onClickRow={handleViewOrderDetail}
      />
    </Box>
  );
}
