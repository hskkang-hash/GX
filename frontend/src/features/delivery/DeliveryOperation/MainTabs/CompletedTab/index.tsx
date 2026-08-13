import { Box } from '@mui/material';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  CustomBtn,
  CustomizableTable,
  CustomModal,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import CustomSelectControlled from '@/components/selects/CustomSelectControlled';
import Colors from '@/configs/Colors';
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

// Constants
const COLUMNS = [
  { Header: 'Order ID', accessor: 'order__id' },
  { Header: 'Order Time', accessor: 'order_time' },
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

export default function CompletedTab() {
  const [showAction, setShowAction] = useState<Record<string, boolean>>({
    complete: false,
  });
  const [selectedTab, setSelectedTab] = useState<string[]>([
    'arrived_order',
    'completed_order',
  ]);
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
  const [theme] = useTheme();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { fetchOperationOrder } = useOperationOrder();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4)],
  });

  const TAB_OPTIONS = [
    { value: ['arrived_order', 'completed_order'], label: t('All') },
    { value: ['arrived_order'], label: t('Arrived Order') },
    { value: ['completed_order'], label: t('Completed Order') },
  ] as const;

  // Handlers
  const handleViewOrderDetail = (row: OrderRow) => {
    if (row.order__id) {
      navigate(
        CustomRoutes.deliveryOperation.subRoutes.orderDetail.path.replace(
          ':id',
          row.id.toString(),
        ) +
          '?orderId=' +
          row.order__id,
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
              label={t('Complete')}
              type="button"
              variant="outline"
              color="primary"
              size="sm"
              disabled={!selectedRows.length}
              onClick={() => setShowAction({ complete: true })}
            />,
          ]
        : [];

    const allArrived = selectedRows.every(
      (row) => row.current_status__code === 'arrived_order',
    );
    const allCompleted = selectedRows.every(
      (row) => row.current_status__code === 'completed_order',
    );

    if (allArrived) {
      return [
        <CustomBtn
          key="verify"
          label={t('Complete')}
          type="button"
          variant="outline"
          color="primary"
          size="sm"
          onClick={() => setShowAction({ complete: true })}
        />,
      ];
    }

    return [];
  };

  const handleCompleteOrder = async () => {
    const formData = { operation_ids: selectedRows.map((row) => row.id) };
    const { success, message } = await API.post(
      endpoint.actionCompletedOrder,
      formData,
    );

    if (success) {
      setRefreshTable(true);
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
      setShowAction({ complete: false });
      ToastTopHelper.success(message || t('Completed Success'));
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

      <CustomModal
        title={t('Confirm Order Completion')}
        show={showAction.complete}
        onHide={() =>
          setShowAction((prevAction) => ({
            ...prevAction,
            complete: false,
          }))
        }
      >
        <div style={{ width: '30rem' }}>
          <div
            style={{
              fontSize: '14px',
              color: theme === 'dark' ? Colors.Gray4 : Colors.Gray6,
            }}
            className=""
          >
            {t('Are you sure you want to mark selected order(s) as completed?')}
          </div>
        </div>
        <ActionBtn
          styles={{ maxWidth: '100%' }}
          leftButtons={[
            <CustomBtn
              type="submit"
              variant="contained"
              color="primary"
              size="lg"
              onClick={handleCompleteOrder}
              label={t('Confirm')}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              onClick={() =>
                setShowAction((prevAction) => ({
                  ...prevAction,
                  complete: false,
                }))
              }
              label={t('Cancel')}
            />,
          ]}
        />
      </CustomModal>
    </Box>
  );
}
