import { Box, Typography } from '@mui/material';
import { useEffect, useRef, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  CustomBtn,
  CustomModal,
  CustomizableTable,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import CustomSelectControlled from '@/components/selects/CustomSelectControlled';
import PaginationSelect from '@/components/selects/PaginationSelect';
import Colors from '@/configs/Colors';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
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
  { Header: 'Order ID', accessor: 'order_id' },
  { Header: 'Order Time', accessor: 'order_time' },
  { Header: 'Sender', accessor: 'sender' },
  { Header: 'Recipient', accessor: 'recipient' },
  { Header: 'Creator', accessor: 'creator' },
  {
    Header: 'Number of Package',
    accessor: 'number_of_packages',
  },
  {
    Header: 'Arrival Time',
    accessor: 'arrival_time',
    filterVariant: 'datetime',
  },
  {
    Header: 'Return Received Time',
    accessor: 'return_received_time',
    filterVariant: 'datetime',
  },
  {
    Header: 'Returned Time',
    accessor: 'returned_time',
    filterVariant: 'datetime',
  },
  {
    Header: 'Created On',
    accessor: 'created_on',
    filterVariant: 'datetime',
  },
  {
    Header: 'Order Created On',
    accessor: 'order__created_on',
    filterVariant: 'datetime',
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

export default function ReturnedTab() {
  const [showAction, setShowAction] = useState<Record<string, boolean>>({
    storage: false,
    return: false,
    process: false,
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
  const [theme] = useTheme();
  const methods = useForm();
  const { control, handleSubmit, formState, watch } = methods;
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { getOptionsByModel } = useCommonAPI();
  const { fetchOperationOrder } = useOperationOrder();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4)],
  });

  const TAB_OPTIONS = [
    {
      value: [
        'order_due_for_returned',
        'order_pending_returned',
        'overdue_order',
        'returned_order',
        'processed_order',
      ],
      label: t('All'),
    },
    {
      value: ['order_due_for_returned'],
      label: t('Order Due for Returned'),
    },
    {
      value: ['order_pending_returned'],
      label: t('Order Pending Returned'),
    },
    { value: ['overdue_order'], label: t('Overdue Order') },
    { value: ['returned_order'], label: t('Returned Order') },
    { value: ['processed_order'], label: t('Processed Order') },
  ] as const;

  const [selectedTab, setSelectedTab] = useState<string[]>(
    TAB_OPTIONS[0].value,
  );

  // Handlers
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
              label={t('Storage')}
              type="button"
              variant="outline"
              color="primary"
              size="sm"
              disabled={!selectedRows.length}
              onClick={() => setShowAction({ storage: true })}
            />,
          ]
        : selectedTab === TAB_OPTIONS[2].value
          ? [
              <CustomBtn
                key="verify"
                label={t('Return')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                disabled={!selectedRows.length}
                onClick={() => setShowAction({ return: true })}
              />,
            ]
          : selectedTab === TAB_OPTIONS[3].value
            ? [
                <CustomBtn
                  key="verify"
                  label={t('Process Order')}
                  type="button"
                  variant="outline"
                  color="primary"
                  size="sm"
                  disabled={!selectedRows.length}
                  onClick={() => setShowAction({ process: true })}
                />,
              ]
            : [];

    const allOrderDueForReturned = selectedRows.every(
      (row) => row.current_status__code === 'order_due_for_returned',
    );
    const allOrderPendingReturned = selectedRows.every(
      (row) => row.current_status__code === 'order_pending_returned',
    );
    const allOverdueOrder = selectedRows.every(
      (row) => row.current_status__code === 'overdue_order',
    );

    if (allOrderDueForReturned) {
      return [
        <CustomBtn
          key="verify"
          label={t('Storage')}
          type="button"
          variant="outline"
          color="primary"
          size="sm"
          onClick={() => setShowAction({ storage: true })}
        />,
      ];
    }

    if (allOrderPendingReturned) {
      return [
        <CustomBtn
          key="verify"
          label={t('Return')}
          type="button"
          variant="outline"
          color="primary"
          size="sm"
          onClick={() => setShowAction({ return: true })}
        />,
      ];
    }

    if (allOverdueOrder) {
      return [
        <CustomBtn
          key="verify"
          label={t('Process Order')}
          type="button"
          variant="outline"
          color="primary"
          size="sm"
          onClick={() => setShowAction({ process: true })}
        />,
      ];
    }

    return [];
  };

  const handleStorageOrder = async () => {
    const storageTerminal = watch('terminal');
    const formData = {
      operation_ids: selectedRows.map((row) => row.id),
      terminal_id: storageTerminal?.value,
    };

    const { success, message } = await API.post(
      endpoint.actionPendingOrder,
      formData,
    );

    if (success) {
      setRefreshTable(true);
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
      setShowAction({
        storage: false,
        return: false,
        process: false,
      });
      navigate(-1);
      ToastTopHelper.success(message || t('Storage Success'));
    }
  };

  const handleReturnOrder = async () => {
    const formData = { operation_ids: selectedRows.map((row) => row.id) };
    const { success, message } = await API.post(
      endpoint.actionReturnedOrder,
      formData,
    );

    if (success) {
      setRefreshTable(true);
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
      setShowAction({
        storage: false,
        return: false,
        process: false,
      });
      navigate(-1);
      ToastTopHelper.success(message || t('Return Order Success'));
    }
  };

  const handleProcessOrder = async () => {
    const formData = { operation_ids: selectedRows.map((row) => row.id) };
    const { success, message } = await API.post(
      endpoint.actionProcessedOrder,
      formData,
    );

    if (success) {
      setRefreshTable(true);
      handleGetOrders({
        pageSize,
        currentPage,
        objSearch,
      });
      setShowAction({
        storage: false,
        return: false,
        process: false,
      });
      navigate(-1);
      ToastTopHelper.success(message || t('Process Order Success'));
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
        onSelectedRows={setSelectedRows}
        objSearch={objSearch}
        setObjSearch={setObjSearch}
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

      <FormProvider {...methods}>
        <form>
          <CustomModal
            title={t('Select Storage Termination')}
            show={showAction.storage}
            onHide={() =>
              setShowAction((prevAction) => ({
                ...prevAction,
                storage: false,
              }))
            }
          >
            <div style={{ width: '45rem' }}>
              <PaginationSelect
                name="terminal"
                label=""
                control={control}
                placeholder={t('Select')}
                loadOptions={getOptionsByModel({
                  name_modal: 'terminal',
                  custom_key: {
                    primary: 'name',
                    secondary: [
                      'street_address',
                      'ward_town_township',
                      'city_county_district',
                      'city_province',
                    ],
                    separator: ', ',
                  },
                })}
                className="flex-fill"
              />
              <Typography
                variant="body1"
                sx={{
                  color: Colors.Gray5,
                  mt: 1,
                }}
              >
                {t(
                  'Please select a terminal to transfer and store the returned order.',
                )}
              </Typography>
            </div>
            <ActionBtn
              styles={{ maxWidth: '100%' }}
              leftButtons={[
                <CustomBtn
                  type="button"
                  variant="contained"
                  color="primary"
                  size="lg"
                  onClick={handleStorageOrder}
                  label={t('Confirm')}
                  style={{ flex: 1 }}
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
                      storage: false,
                    }))
                  }
                  label={t('Cancel')}
                  style={{ flex: 1 }}
                />,
              ]}
            />
          </CustomModal>

          <CustomModal
            title={t('Confirm Order Return')}
            show={showAction.return}
            onHide={() =>
              setShowAction((prevAction) => ({
                ...prevAction,
                return: false,
              }))
            }
          >
            <div style={{ width: '30rem' }}>
              <div
                style={{
                  fontSize: '14px',
                  color: theme === 'dark' ? Colors.Gray4 : Colors.Gray6,
                }}
              >
                {t(
                  'Are you sure you want to confirm that selected order(s) has been returned to the customer?',
                )}
              </div>
            </div>
            <ActionBtn
              styles={{ maxWidth: '100%' }}
              leftButtons={[
                <CustomBtn
                  type="button"
                  variant="contained"
                  color="primary"
                  size="lg"
                  onClick={handleReturnOrder}
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
                      return: false,
                    }))
                  }
                  label={t('Cancel')}
                />,
              ]}
            />
          </CustomModal>

          <CustomModal
            title={t('Confirm Order Processing')}
            show={showAction.process}
            onHide={() =>
              setShowAction((prevAction) => ({
                ...prevAction,
                process: false,
              }))
            }
          >
            <div style={{ width: '30rem' }}>
              <div
                style={{
                  fontSize: '14px',
                  color: theme === 'dark' ? Colors.Gray4 : Colors.Gray6,
                }}
              >
                {t(
                  'This order has been pending for an extended period without customer pickup. Do you want to proceed with processing selected order(s)?',
                )}
              </div>
            </div>
            <ActionBtn
              styles={{ maxWidth: '100%' }}
              leftButtons={[
                <CustomBtn
                  type="button"
                  variant="contained"
                  color="primary"
                  size="lg"
                  onClick={handleProcessOrder}
                  label={t('Yes')}
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
                      process: false,
                    }))
                  }
                  label={t('Cancel')}
                />,
              ]}
            />
          </CustomModal>
        </form>
      </FormProvider>
    </Box>
  );
}
