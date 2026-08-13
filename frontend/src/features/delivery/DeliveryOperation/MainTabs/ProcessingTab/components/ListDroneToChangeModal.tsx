import { Box, Radio } from '@mui/material';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CustomBtn, CustomizableTable, CustomModal, useTheme } from 'rj-core';

import Truncate from '@/components/truncate/Truncate';
import API, { endpoint } from '@/services/API';
import { isEmptyObject } from '@/utils/fetchFromObject';

// Define interface for search params
interface SearchParam {
  id: string;
  value: string | number | boolean;
}

// Define interface for sort params
interface SortParam {
  id: string;
  desc: boolean;
}

// Define interface for the search object
interface SearchObject {
  searchParams?: SearchParam[];
  filters?: Record<string, unknown>;
  sortParams?: SortParam[];
}

export default function ListDroneToChangeModal({
  droneId,
  orderIds,
  routeId,
  show,
  onClose,
  onChangeDroneSuccess,
}: {
  droneId: number;
  orderIds: number[];
  routeId: number;
  show: boolean;
  onClose: () => void;
  onChangeDroneSuccess: () => void;
  
}) {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [pageSize, setPageSize] = useState<number>(10);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [objSearch, setObjSearch] = useState({});
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const [droneList, setDroneList] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  const handleChangeDrone = async (selectedDroneId: number) => {
    setIsSubmitting(true);
    try {
      const response = await API.post(endpoint.changeDrone, {
        from_drone: droneId,
        order_ids: orderIds,
        to_drone: selectedDroneId,
        route_id: routeId,
      });
      if (response.success) {
        onChangeDroneSuccess();
        onClose();
      }
    } catch (error) {
      console.log(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const columns = [
    {
      Header: '',
      accessor: 'action',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: { width: '2rem' },
      cell: (info: any) => {
        return (
          <Box
            display="flex"
            justifyContent="center"
          >
            <Radio
              onChange={() => handleChangeDrone(info.row.original.id)}
              sx={{
                color: '#2196F3',
                padding: 0,
                '&.Mui-checked': { color: '#2196F3' },
              }}
            />
          </Box>
        );
      },
    },
    {
      Header: t('Name'),
      accessor: 'name',
    },
    {
      Header: t('Modal'),
      accessor: 'model',
    },
    {
      Header: t('Battery'),
      accessor: 'battery_capacity',
    },
    {
      Header: t('Maximum Load'),
      accessor: 'payload_capacity',
    },
  ];

  const fetchDroneList = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch: any;
  }) => {
    const paramsFetch: {
      page_size: number;
      current_page: number;
      filters?: Record<string, unknown>;
      sort_obj?: SortParam[];
      [key: string]: unknown;
    } = {
      page_size: pageSize,
      current_page: currentPage,
    };

    if (objSearch) {
      if (objSearch?.searchParams) {
        objSearch?.searchParams.forEach((item: SearchParam) => {
          paramsFetch[item.id] = item.value;
        });
      }
      if (objSearch?.filters) {
        paramsFetch['filters'] = objSearch.filters;
      }
      if (objSearch?.sortParams && objSearch?.sortParams.length) {
        paramsFetch.sort_obj = objSearch.sortParams;
      }
    }

    const response = await API.post(
      endpoint.changeDrone,
      {
        from_drone: droneId,
        order_ids: orderIds,
        route_id: routeId,
      },
      {
        params: paramsFetch,
      },
    );
    console.log(response);
    setDroneList({
      data: response.data,
      totalItem: response.total_items,
      totalPage: response.total_pages,
    });
  };
  console.log('routeId', routeId);

  useEffect(() => {
    if (
      show &&
      droneId &&
      orderIds &&
      routeId &&
      !isEmptyObject(objSearch) &&
      pageSize &&
      currentPage
    ) {
      fetchDroneList({
        pageSize: pageSize,
        currentPage: currentPage,
        objSearch: objSearch,
      });
    }
  }, [objSearch, pageSize, currentPage, show, droneId, orderIds, routeId]);

  return (
    <CustomModal
      title={t('Change Drone')}
      show={show}
      onHide={onClose}
    >
      <Box
        width="50vw"
        maxWidth="800px"
        display="flex"
        flexDirection="column"
        alignItems="center"
        gap={1}
        pb={1}
      >
        <Box width="100%">
          <CustomizableTable
            subTable={true}
            notShowSelectRow
            columns={columns}
            data={droneList}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            pageSize={pageSize}
            setPageSize={setPageSize}
            useSystemSetting
          />
        </Box>

        <CustomBtn
          label={t('Cancel')}
          variant="outline"
          color="secondary"
          size="lg"
          style={{ width: '10rem' }}
          onClick={onClose}
        />
      </Box>
    </CustomModal>
  );
}
