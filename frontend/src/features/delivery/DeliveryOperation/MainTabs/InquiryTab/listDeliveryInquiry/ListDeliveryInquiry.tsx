import { Box } from '@mui/material';
import { t } from 'i18next';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  CustomizableTable,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import CustomSelectControlled from '@/components/selects/CustomSelectControlled';
import API, { endpoint } from '@/services/API';
import { formatStatus } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import useAPI from '../useAPI';
import './ListDeliveryInquiry.scss';

const ListDeliveryInquiry = () => {
  const [theme] = useTheme();
  const navigate = useNavigate();
  const headerPageRef = useRef(null);
  const searchCardRef = useRef(null);
  const { getListOrderDetail } = useAPI();
  const [objSearch, setObjSearch] = useState({});
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const [selectedTab, setSelectedTab] = useState<string[]>([
    'delivered',
    'pending_confirmation',
    'pending_processing',
    'awaiting_payment',
    'awaiting_shipment',
    'returned',
    'cancelled',
  ]);

  useEffect(() => {
    const test = async () => {
      const response = await API.get(endpoint.getDataForSelectInput, {
        params: {
          model_name: 'orderstatus',
          multi_language: true,
          search_term: '',
          page_number: 1,
          page_size: 10,
          distinct: true,
          search_field: '',
        },
      });
    };
    test();
  }, []);

  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [showAdvancedSearch, setShowAdvancedSearch] = useState<boolean>(false);

  // use for save searchcondition
  const location = useLocation();
  const { data: dataSearchCondition } = location.state || {};

  // Constants
  const TAB_OPTIONS = [
    {
      value: [
        'delivered',
        'pending_confirmation',
        'pending_processing',
        'awaiting_payment',
        'awaiting_shipment',
        'returned',
        'cancelled',
      ],
      label: t('All'),
    },
    { value: ['delivered'], label: t('Delivered') },
    { value: ['pending_confirmation'], label: t('Pending Confirmation') },
    { value: ['pending_processing'], label: t('Pending Processing') },
    { value: ['awaiting_payment'], label: t('Awaiting Payment') },
    { value: ['awaiting_shipment'], label: t('Awaiting Shipment') },
    { value: ['returned'], label: t('Returned') },
    { value: ['cancelled'], label: t('Cancelled') },
  ] as const;

  useEffect(() => {
    if (dataSearchCondition) {
      setObjSearch(dataSearchCondition);
    }
  }, [dataSearchCondition]);

  //end

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  const fetchData = async () => {
    const objSearchFetch = {
      ...objSearch,
      status_code: selectedTab,
    };
    console.log('objSearchFetch', objSearchFetch);

    const { success, data, message } = await getListOrderDetail({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearchFetch,
    });

    if (success) {
      setData(data);
    }

    if (!success) {
      ToastTopHelper.error(message);
    }
  };

  useEffect(() => {
    if (pageSize && selectedTab) {
      fetchData();
    }
  }, [pageSize, currentPage, objSearch, selectedTab]);

  const handleSelectionRows = (selectedData: any) => {
    setSelectedRows(selectedData);
  };

  const handleViewDetailDevice = (selectedRow: any) => {
    navigate(`/delivery-inquiry/${selectedRow.id}`, {
      state: { id: selectedRow.id },
    });
  };

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchCardRef],
    additionalHeights: [remToPx(8)],
  });

  const HistoryBehaviorColumns = [
    {
      Header: 'Order ID',
      accessor: 'order_code',
      cell: (row: any) => {
        return row?.row?.original?.order_code ? (
          <span>{row?.row?.original?.order_code}</span>
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Order Time',
      accessor: 'created_on',
      filterVariant: 'datetime',
    },
    {
      Header: 'Sender',
      accessor: 'sender_name',
      cell: (row: any) => {
        return row?.row?.original?.sender_name ? (
          <span>{row?.row?.original?.sender_name}</span>
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Recipient',
      accessor: 'recipient_name',
      cell: (row: any) => {
        return row?.row?.original?.recipient_name ? (
          <span>{row?.row?.original?.recipient_name}</span>
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Number of Packages',
      accessor: 'item_count',
      cell: (row: any) => {
        return row?.row?.original?.item_count ? (
          <span>{row?.row?.original?.item_count}</span>
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Status',
      accessor: 'status__name',
      filterOptions: [
        'delivered',
        'pending_confirmation',
        'awaiting_shipment',
        'cancelled',
        'pending_processing',
        'awaiting_payment',
        'returned',
      ],
      cell: (row: any) =>
        formatStatus(row?.row?.original?.status__code, theme, t),
    },
  ];

  return (
    <Box px="1rem">
      <CustomizableTable
        stickyHeader
        notShowSelectRow
        availableHeight={spaceTableHeight}
        columns={HistoryBehaviorColumns}
        data={data}
        objSearch={objSearch}
        setObjSearch={setObjSearch}
        onClickRow={handleViewDetailDevice}
        onSelectedRows={handleSelectionRows}
        refreshTable={refreshTable}
        setRefreshTable={setRefreshTable}
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        pageSize={pageSize}
        setPageSize={setPageSize}
        offcanvas={openOffcanvas}
        setOpenOffcanvas={(boolean: boolean) => {
          setOpenOffcanvas(boolean);
        }}
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
      />
    </Box>
  );
};
export default ListDeliveryInquiry;
