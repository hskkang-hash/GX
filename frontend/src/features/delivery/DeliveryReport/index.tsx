import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  Container,
  CustomBtn,
  CustomizableTable,
  CustomModal,
  HeaderWithBtn,
  Main,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import Colors from '@/configs/Colors';
import API, { CustomRoutes, endpoint } from '@/services/API';
import { getContrastTextColor, remToPx } from '@/utils/utils';

import { formatStatusDeliveryInquiry } from '../deliveryInquiry/utils/StatusColorInquiry';
import { useCompletedOrders } from './hooks/useCompletedOrders';

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

// Base columns without action column
const BASE_COLUMNS = [
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
    Header: 'Mapped Status',
    accessor: 'mapped_status',
    enableColumnFilter: false,
    cell: (info: any) => {
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

export default function DeliveryReport() {
  const [showAction, setShowAction] = useState<Record<string, boolean>>({
    complete: false,
  });
  const [selectedTab, setSelectedTab] = useState<string[]>([
    'arrived_order',
    'completed_order',
  ]);
  const [selectedRows, setSelectedRows] = useState<OrderRow[]>([]);
  const [pageSize, setPageSize] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [objSearch, setObjSearch] = useState<Record<string, any>>({});
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [data, setData] = useState<TableData>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);

  // Hooks
  const [theme] = useTheme();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { fetchDeliveryReport } = useCompletedOrders();
  const headerPageRef = useRef<HTMLDivElement>(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  // Handlers
  const handleViewOrderDetail = (row: OrderRow) => {
    if (row.order_id) {
      navigate(
        CustomRoutes.deliveryReport.subRoutes.completedOrderDetail.path.replace(
          ':id',
          row.id.toString(),
        ) +
          '?orderId=' +
          row.order_id,
      );
    }
  };

  const [downloadingIds, setDownloadingIds] = useState<Set<number>>(new Set());

  const handleDownloadReport = async (id: number) => {
    try {
      setDownloadingIds((prev) => new Set(prev).add(id));
      const response = await API.get(endpoint.downloadReport(id));

      if (response.success && response.data?.file_url) {
        const fileUrl = response.data.file_url;
        const fileName = response.data.file_name || `report-${id}.pdf`;

        const fileResponse = await fetch(fileUrl);
        const blob = await fileResponse.blob();

        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        window.URL.revokeObjectURL(url);

        ToastTopHelper.success(t('Report downloaded successfully'));
      } else {
        ToastTopHelper.error(response.data.message);
      }
    } catch (error) {
      ToastTopHelper.error(t('Failed to download report'));
    } finally {
      setDownloadingIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(id);
        return newSet;
      });
    }
  };

  // Define columns inside component to access handleDownloadReport
  const COLUMNS = [
    ...BASE_COLUMNS,
    {
      Header: t(' '),
      accessor: 'action',
      enableSorting: false,
      enableColumnFilter: false,
      notUseConfigTable: true,
      customStyle: {
        width: '10rem',
      },
      cell: (row: any) => {
        const rowId = row?.row?.original?.id;
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
              label={t('Download Report')}
              type="button"
              size="sm"
              loading={downloadingIds.has(rowId)}
              onClick={() => handleDownloadReport(rowId)}
            />
          </div>
        );
      },
    },
  ];

  const handleGetOrders = async ({
    pageSize,
    currentPage,
    objSearch,
  }: SearchParams) => {
    const response = await fetchDeliveryReport({
      pageSize,
      currentPage,
      objSearch,
    });

    if (response) {
      setData({
        data: response.data,
        totalPage: response.totalPage,
        totalItem: response.totalItem,
      });
    }
  };

  const handleCompleteOrder = async () => {
    const formData = { operation_ids: selectedRows.map((row) => row.id) };
    const { success, message } = await API.post(
      endpoint.actionCompletedOrder,
      formData,
    );

    if (success) {
      setRefreshTable(true);
      if (pageSize) {
        handleGetOrders({
          pageSize,
          currentPage,
          objSearch,
        });
      }
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
    <Container isOpenCanvas={openOffcanvas}>
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[]}
      />
      <Main>
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
          offcanvas={openOffcanvas}
          setOpenOffcanvas={(boolean: boolean) => {
            setOpenOffcanvas(boolean);
          }}
          // buttons={[
          //   <CustomBtn
          //     key="verify"
          //     label={t('Complete')}
          //     type="button"
          //     variant="outline"
          //     color="primary"
          //     size="sm"
          //     disabled={!selectedRows.length}
          //     onClick={() => setShowAction({ complete: true })}
          //   />,
          // ]}
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
              {t(
                'Are you sure you want to mark selected order(s) as completed?',
              )}
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
      </Main>
    </Container>
  );
}
