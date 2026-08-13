import { ConfigProvider } from 'antd';
import 'dayjs/locale/en';
import 'dayjs/locale/ko';
import 'dayjs/locale/th';
import { t } from 'i18next';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Container,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  SearchCard,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import Colors from '@/configs/Colors';
import { formatStatusEtri } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import useAPI from '../useAPI/useAPI';
import './ListEtriOrder.scss';

const ListEtriOrder = () => {
  const [objSearch, setObjSearch] = useState({});
  const navigate = useNavigate();
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const listId = selectedRows?.map((item: any) => item.id).join(',');

  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [showAdvancedSearch, setShowAdvancedSearch] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);

  const { fetchTrackOperationOrder } = useAPI();

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  // use for save searchcondition
  const location = useLocation();
  const { data: dataSearchCondition } = location.state || {};

  useEffect(() => {
    if (dataSearchCondition) {
      setObjSearch(dataSearchCondition);
    }
  }, [dataSearchCondition]);
  //end

  const fetchData = async ({
    objSearch,
    pageSize,
    currentPage,
  }: {
    objSearch: any;
    pageSize: number;
    currentPage: number;
  }) => {
    const { success, data, message } = await fetchTrackOperationOrder({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearch,
      status_codes: ['unverified_order', 'verified_order'],
    });

    if (success) {
      console.log('data_fetchOperationOrder', data);
      setData(data);
    }

    if (!success) {
      ToastTopHelper.error(message || 'Expected error');
    }
  };

  const [theme] = useTheme();

  const HistoryBehaviorColumns = [
    {
      Header: 'Receipt Number',
      accessor: 'receipt_number',
      enableColumnFilter: false,
      enableSorting: false,
      customStyle: {
        verticalAlign: 'top',
      },
      cell: (row: any) => {
        return row?.row?.original?.order__another_info?.etri?.receipt_id ? (
          <span>
            {row?.row?.original?.order__another_info?.etri?.receipt_id}
          </span>
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Created Date',
      accessor: 'created_on',
      filterVariant: 'datetime',
      enableColumnFilter: false,
      enableSorting: false,
    },
    {
      Header: 'Sender',
      accessor: 'sender',
      enableColumnFilter: false,
      enableSorting: false,
      cell: (row: any) => {
        return row?.row?.original?.order__sender_name ? (
          <span>{row?.row?.original?.order__sender_name}</span>
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Receiver',
      accessor: 'receiver',
      enableColumnFilter: false,
      enableSorting: false,
      cell: (row: any) => {
        return row?.row?.original?.order__recipient_name ? (
          <span>{row?.row?.original?.order__recipient_name}</span>
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Handler',
      accessor: 'handler',
      enableColumnFilter: false,
      enableSorting: false,
      cell: (row: any) => {
        return row?.row?.original?.modified_by__last_name &&
          row?.row?.original?.modified_by__first_name ? (
          <span>
            {row?.row?.original?.modified_by__last_name +
              ' ' +
              row?.row?.original?.modified_by__first_name}
          </span>
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Status',
      accessor: 'mapped_status',
      enableColumnFilter: false,
      cell: (row: any) =>
        formatStatusEtri(row?.row?.original?.mapped_status, t),
    },
    {
      Header: 'Note',
      accessor: 'note',
      enableColumnFilter: false,
      enableSorting: false,
      cell: (row: any) => {
        return row?.row?.original?.order__recipient_note ? (
          <span>{row?.row?.original?.order__recipient_note}</span>
        ) : (
          '-'
        );
      },
    },
  ];

  useEffect(() => {
    if (pageSize) {
      fetchData({ objSearch, pageSize, currentPage });
    }
  }, [pageSize, currentPage, objSearch]);

  const handleSelectionRows = (selectedData: any) => {
    setSelectedRows(selectedData);
  };

  const handleViewDetailDevice = (selectedRow: any) => {
    console.log('selectedRow', selectedRow);
    const detailPath = `/etri-tracking/${selectedRow.order__id}/${selectedRow.id}`;
    // Pass receive_data as orderMap for backward compatibility
    // DetailEtriOrder will extract from detailOrder.another_info.etri.receive_data anyway
    navigate(detailPath, {
      state: {
        id: selectedRow.order__id,
        orderMap: selectedRow?.order__another_info?.etri?.receive_data || 
                  selectedRow?.order__another_info?.etri?.transmission_data,
      },
    });
  };

  const headerPageRef = useRef(null);
  const searchCardRef = useRef(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchCardRef],
    additionalHeights: [remToPx(8)],
  });

  const ListStatus = [
    {
      label: 'Delivery Completed',
      value: t('etri.Delivery Completed'),
    },
    {
      label: 'Delivery Cancelled',
      value: t('etri.Delivery Cancelled'),
    },
    {
      label: 'In Delivery',
      value: t('etri.In Delivery'),
    },
    {
      label: 'Waiting for Delivery',
      value: t('etri.Waiting for Delivery'),
    },
    {
      label: 'Receipt Completed',
      value: t('etri.Receipt Completed'),
    },
    {
      label: 'Receipt Cancelled',
      value: t('etri.Receipt Cancelled'),
    },
  ];

  const [activeStatus, setActiveStatus] = useState<string>('');
  const prefixConditionsAfter = () => {
    return (
      <ConfigProvider
        theme={{
          components: {
            Select: {
              selectorBg: theme === 'dark' ? '#212529' : '#fff',
              optionActiveBg:
                theme === 'dark'
                  ? 'var(--ga-light-theme-font-color)'
                  : 'var(--ga-primary-3)',
              optionSelectedBg:
                theme === 'dark'
                  ? 'var(--ga-light-theme-font-color)'
                  : 'var(--ga-primary-3)',
              hoverBorderColor:
                theme === 'dark' ? '#444646' : 'var(--ga-primary)',
              optionSelectedColor:
                theme === 'dark' ? '#fff' : 'var(--ga-primary)',
            },
            Input: {
              colorBorder: theme === 'dark' ? '#444646' : '#dee2e6',
              hoverBorderColor:
                theme === 'dark' ? '#444646' : 'var(--ga-primary)',
            },
          },

          token: {
            colorPrimary: Colors.Primary,
            colorText: theme === 'dark' ? '#fff' : '#000',
            colorBorder: theme === 'dark' ? '#444646' : '#dee2e6',
            colorTextPlaceholder: theme === 'dark' ? '#444646' : '#dee2e6',
            controlHeight: 30,
          },
        }}
      >
        {ListStatus.map((item, index) => (
          <div
            key={index}
            onClick={() => {
              if (activeStatus === item.value) {
                setActiveStatus('');
              } else {
                setActiveStatus(item.value);
              }
            }}
            style={{
              textWrap: 'nowrap',
            }}
            className={`status-etri-style ${theme === 'dark' ? 'theme-dark' : ''
              } ${activeStatus === item.value ? 'active-status' : ''}`}
          >
            {t(`etri.${item.label}`)}
          </div>
        ))}
      </ConfigProvider>
    );
  };

  const handleClickSearch = (dateTime: {
    startDate: string;
    endDate: string;
  }) => {
    setObjSearch((prevState: any) => ({
      ...prevState,
      startDate: dateTime?.startDate || null,
      endDate: dateTime?.endDate || null,
      mapped_status: activeStatus,
    }));
    setCurrentPage(1);
  };

  return (
    <Container
      id="list-track-order"
      isOpenCanvas={openOffcanvas || showAdvancedSearch}
    >
      <HeaderWithBtn ref={headerPageRef} />
      <Main>
        <SearchCard
          title={t('Created Date')}
          ref={searchCardRef}
          hideAdvancedSearch
          hideClean
          hideTimeHelper
          prefixConditionsAfter={prefixConditionsAfter}
          setObjSearch={setObjSearch}
          objSearch={objSearch}
          handleClickSearch={handleClickSearch}
        />
        <div className="list-track-order__table-container">
          <CustomizableTable
            stickyHeader
            availableHeight={spaceTableHeight}
            columns={HistoryBehaviorColumns}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            useSystemSetting
            subTable
            notShowSelectRow
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
          />
        </div>
      </Main>
    </Container>
  );
};
export default ListEtriOrder;
