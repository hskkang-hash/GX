import { t } from 'i18next';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { GoPlus } from 'react-icons/go';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBtn,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  ToastTopHelper,
  useCalculateHeight,
  ROLE_PERMISSION,
} from 'rj-core';

import useAPI from '@/features/packaging/useAPI/useAPI';
import { isEmptyObject } from '@/utils/fetchFromObject';
import { formatEnabled } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

const HistoryBehaviorColumns = [
  {
    Header: 'ID',
    accessor: 'id',
  },
  {
    Header: 'Package Name',
    accessor: 'name',
    cell: (row: any) => {
      console.log('row_in_main_type', row?.row?.original);
      return row.getValue() ? <span>{row.getValue()}</span> : '-';
    },
  },
  {
    Header: 'Active',
    accessor: 'active',
    filterVariant: 'checkbox',
    filterOptions: ['True', 'False'],
    cell: (row: any) => formatEnabled(row?.row?.original?.active),
  },
  {
    Header: 'Created On',
    accessor: 'created_on',
    filterVariant: 'datetime',
  },
  {
    Header: 'Dimensions',
    accessor: 'dimensions',
    cell: (row: any) => {
      return row.getValue() ? <span>{row.getValue()}</span> : '-';
    },
  },
  {
    Header: 'Max Weight',
    accessor: 'max_weight',
    cell: (row: any) => {
      return row.getValue() ? <span>{row.getValue()}</span> : '-';
    },
  },
  {
    Header: 'Packaging Type',
    accessor: 'package_type__name',
    cell: (row: any) => {
      return row.getValue() ? <span>{row.getValue()}</span> : '-';
    },
  },
  {
    Header: 'Waterproof',
    accessor: 'water_proof',
    cell: (row: any) => {
      return row.getValue() ? <span>{row.getValue()}</span> : '-';
    },
  },
  {
    Header: 'Fragile',
    accessor: 'fragile',
    filterVariant: 'checkbox',
    filterOptions: ['True', 'False'],
    cell: (row: any) => formatEnabled(row?.row?.original?.fragile),
  },
  {
    Header: 'Note',
    accessor: 'note',
    cell: (row: any) => {
      return row.getValue() ? <span>{row.getValue()}</span> : '-';
    },
  },
];

const ListPackaging = () => {
  const [objSearch, setObjSearch] = useState({});
  const navigate = useNavigate();
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const listId = useMemo(
    () => selectedRows?.map((item: any) => item.id).join(','),
    [selectedRows],
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);

  const {
    getPackagingSpecifications,
    activePackagingAPI,
    deactivePackagingAPI,
  } = useAPI();

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
    setLoading(true);
    const { success, data, message } = await getPackagingSpecifications({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearch,
    });

    if (success) {
      setLoading(false);
      setData(data);
    }

    if (!success) {
      ToastTopHelper.error(message);
    }
  };

  useEffect(() => {
    pageSize && !isEmptyObject(objSearch) && fetchData();
  }, [pageSize, currentPage, objSearch]);

  const handleSelectionRows = (selectedData: any) => {
    setSelectedRows(selectedData);
  };

  const handleViewDetailDevice = (selectedRow: any) => {
    if (selectedRow.active) {
      navigate(`/packaging/detail-packaging/${selectedRow.id}`, {
        state: { id: selectedRow.id },
      });
    }
  };

  const handleActionPackaging = useCallback(
    async (action: 'activate' | 'deactivate') => {
      const { success, message } = await (
        action === 'activate' ? activePackagingAPI : deactivePackagingAPI
      )({
        ids: listId,
        useLoading: true,
      });

      if (success) {
        const updatedData = data.data.map((item) => {
          const found = selectedRows.find((row: any) => row.id === item.id);
          if (found) {
            return {
              ...item,
              active: action === 'activate' ? true : false,
            };
          }
          return item;
        });

        setData({
          ...data,
          data: updatedData,
        });

        setRefreshTable(true);
        // setHideDeactivateModal();
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [data.data, selectedRows], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const headerPageRef = useRef(null);
  const searchCardRef = useRef(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchCardRef],
    additionalHeights: [remToPx(8)],
  });

  return (
    <Container
      id="list-packaging"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Add New Packaging Specification')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => navigate('/packaging/add-new-packaging')}
          />,
        ]}
      />

      <Main>
        <div className="list-packaging__table-container">
          <CustomizableTable
            stickyHeader
            availableHeight={spaceTableHeight}
            columns={HistoryBehaviorColumns}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleViewDetailDevice}
            onSelectedRows={handleSelectionRows}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            buttons={[
              <CustomBtn
                label={t('Activate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionPackaging('activate')}
              />,
              <CustomBtn
                label={t('Deactivate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionPackaging('deactivate')}
              />,
            ]}
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
export default ListPackaging;
