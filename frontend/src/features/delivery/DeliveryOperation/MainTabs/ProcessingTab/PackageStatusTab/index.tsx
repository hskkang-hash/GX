import { Box } from '@mui/material';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import {
  CustomizableTable,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import API, { endpoint } from '@/services/API';
import { formatStatus } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import { useOperationOrder } from '../../../hooks/useOperationOrder';
import OrderDetailModal from '../components/OrderDetailModal';
import PackageStatusModal from '../components/PackageStatusModal';

// Types
interface OrderRow {
  id: number;
  order_id: string;
  current_status__code: string;
  order_time: string;
  sender: string;
  recipient: string;
  creator: string;
  number_of_packages: number;
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

interface SearchParams {
  pageSize: number;
  currentPage: number;
  objSearch: Record<string, unknown>;
}

export type PackageAttribute = {
  id: number;
  name: string;
  value: string;
};

export type Package = PackageAttribute[];

export type PackageList = Package[];

export default function PackageStatusTab() {
  const [selectedOrder, setSelectedOrder] = useState<OrderRow | null>(null);

  console.log('selectedOrder', selectedOrder);
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
  const [isDetailModalOpenEye, setIsDetailModalOpenEye] = useState(false);
  const [selectedRowForDetail, setSelectedRowForDetail] =
    useState<OrderRow | null>(null);

  // Hooks
  const [theme] = useTheme();
  const { t } = useTranslation();
  const { fetchTransitOrder, fetchPackageProcessingStatus, confirmPackage } =
    useOperationOrder();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4), remToPx(1), 400],
  });

  const COLUMNS = [
    { Header: 'Order ID', accessor: 'order__order_code' },
    {
      Header: 'Order Time',
      accessor: 'order__created_on',
      filterVariant: 'datetime',
    },
    { Header: 'Origin', accessor: 'origin' },
    { Header: 'Destination', accessor: 'destination' },
    { Header: 'Sender', accessor: 'order__sender_name' },
    { Header: 'Recipient', accessor: 'order__recipient_name' },
    { Header: 'Creator', accessor: 'handler' },
    // {
    //   Header: 'Mapped Status',
    //   accessor: 'mapped_status',
    //   enableColumnFilter: false,
    //   cell: (info) => {
    //     const { t } = useTranslation();
    //     const mappedListStatus = info.row.original?.mapped_status_list;
    //     const mappedStatusCode = info.row.original?.mapped_status_code;
    //     const currentStatusName = info.row.original?.mapped_status;
    //     const currentTextColor = getContrastTextColor(
    //       info.row.original?.mapped_status_background_color,
    //     );
    //     const currentBackgroundColor =
    //       info.row.original?.mapped_status_background_color;
    //     const currentBorderColor =
    //       info.row.original?.mapped_status_border_color;

    //     return (
    //       <div
    //         style={{
    //           display: 'flex',
    //           gap: 8,
    //           width: 'fit-content',
    //           flexFlow: 'wrap',
    //         }}
    //       >
    //         {mappedListStatus?.length > 0
    //           ? mappedListStatus?.map(
    //               (item: {
    //                 name: string;
    //                 code: string;
    //                 background_color: string;
    //                 text_color: string;
    //                 border_color: string;
    //               }) =>
    //                 formatStatusDeliveryInquiry({
    //                   t,
    //                   status_name: item.name,
    //                   status_code: mappedStatusCode,
    //                   backgroundColor: item.background_color,
    //                   color: item.text_color,
    //                   border: item.border_color,
    //                   isShowButton: false,
    //                 }),
    //             )
    //           : mappedStatusCode &&
    //             formatStatusDeliveryInquiry({
    //               t,
    //               status_name: currentStatusName,
    //               status_code: mappedStatusCode,
    //               backgroundColor: currentBackgroundColor,
    //               color: currentTextColor,
    //               border: currentBorderColor,
    //               isShowButton: false,
    //             })}
    //       </div>
    //     );
    //   },
    // },
    // {
    //   Header: 'Delivery Device',
    //   accessor: 'delivery_device',
    //   cell: (row) => {
    //     console.log('row', row.row.original.delivery_device);
    //     return (
    //       <div>
    //         {row.row.original.delivery_device
    //           ?.map((item) => item.id)
    //           .join(', ')}
    //       </div>
    //     );
    //   },
    // },
    {
      Header: 'Number of Package',
      accessor: 'number_of_packages',
    },
    // {
    //     Header: t(" "),
    //     accessor: "action",
    //     cell: (row: any) => (
    //         <div
    //             className="special-label"
    //             onClick={(e) => {
    //                 e.stopPropagation();
    //                 fetchOrderDetail(row?.row?.original.order__id);
    //                 setIsDetailModalOpen(true);
    //             }}
    //         >
    //             <BsEye size={16} />
    //         </div>
    //     ),
    //     customStyle: { maxWidth: 20, textAlign: "center" },
    //     enableSorting: false,
    //     enableColumnFilter: false,
    //     notUseConfigTable: true,
    // },
    {
      Header: t(' '),
      accessor: 'action',
      cell: (row: { row: { original: OrderRow } }) => (
        <div
          className="special-label"
          onClick={(e) => {
            e.stopPropagation();
            fetchOrderDetailEye(row.row.original.order_id);
            setIsDetailModalOpenEye(true);
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

  const fetchOrderDetailEye = async (orderId: string) => {
    const { success, data } = await API.get(endpoint.detailOrder(orderId));
    if (success) {
      setSelectedRowForDetail(data);
    }
  };

  // Handlers
  const handleViewOrderDetail = async (row: OrderRow) => {
    setSelectedOrder(row);
    fetchOrderDetail(row?.order_id);
    setIsDetailModalOpen(true);
  };

  const fetchOrderDetail = async (orderId: string) => {
    const { success, data } = await API.get(endpoint.detailOrder(orderId));
    if (success) {
      setSelectedRowForDetail(data);
    }
  };

  const handleGetOrders = async ({
    pageSize,
    currentPage,
    objSearch,
  }: SearchParams) => {
    const objSearchFetch = {
      ...objSearch,
      status_codes: ['select_route_processing'],
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
    }
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

  const [packageStatusList, setPackageStatusList] = useState<PackageList>([]);
  const [loadingPackages, setLoadingPackages] = useState<Set<string>>(
    new Set(),
  );

  const getPackageProcessingStatus = async (operation_item_id: number) => {
    const { success, data } =
      await fetchPackageProcessingStatus(operation_item_id);
    if (success) {
      const formatData = data?.map((item: any) => [
        {
          id: item.id,
          name: 'Package ID',
          value: item.order_item__code,
        },
        { id: 2, name: 'Device ID', value: item.drone__name },
        {
          id: 3,
          name: 'Package Status (Device)',
          value:
            item?.is_delivered_by_drone == true
              ? formatStatus('arrived', theme, t)
              : '-',
        },
        {
          id: 4,
          name: 'Arrival Time',
          value: item?.drone_arrived_at ? item?.drone_arrived_at : '-',
        },
        {
          id: 5,
          name: 'Package Status (User)',
          value:
            item?.is_arrived == true
              ? formatStatus('delivered', theme, t)
              : '-',
        },
        { id: 6, name: 'User', value: item?.created_by__username },
        {
          id: 7,
          name: 'Check Time',
          value: item?.arrived_at ? item.arrived_at : '-',
        },
      ]);
      setPackageStatusList(formatData);
    }
  };

  useEffect(() => {
    if (selectedOrder) {
      getPackageProcessingStatus(selectedOrder?.id);
    }
  }, [selectedOrder]);

  const handleCompletePackage = async (packageRequest: Package) => {
    const packageIdAttr = packageRequest.find(
      (attr) => attr.name === 'Package ID',
    );

    if (!packageIdAttr) {
      ToastTopHelper.error(t('Package ID not found.'));
      return;
    }
    console.log('packageIdAttr', packageRequest, packageIdAttr);
    const packageId = packageIdAttr.value;

    // Set loading for this specific package
    setLoadingPackages((prev) => new Set(prev).add(packageId));

    try {
      console.log('packageIdAttr', packageRequest, packageIdAttr);
      const { success, message } = await confirmPackage({
        package_id: packageIdAttr.id,
      });

      if (success) {
        getPackageProcessingStatus(selectedOrder?.id);

        if (pageSize) {
          handleGetOrders({
            pageSize,
            currentPage,
            objSearch,
          });
        }
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    } finally {
      // Remove loading for this specific package
      setLoadingPackages((prev) => {
        const newSet = new Set(prev);
        newSet.delete(packageId);
        return newSet;
      });
      setIsDetailModalOpen(false);
    }
  };

  return (
    <Box>
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
      <PackageStatusModal
        show={isDetailModalOpen}
        onHide={() => setIsDetailModalOpen(false)}
        detailData={packageStatusList}
        handleCompletePackage={handleCompletePackage}
        loadingPackages={loadingPackages}
      />
      <OrderDetailModal
        show={isDetailModalOpenEye}
        onHide={() => setIsDetailModalOpenEye(false)}
        detailData={selectedRowForDetail}
      />
    </Box>
  );
}
