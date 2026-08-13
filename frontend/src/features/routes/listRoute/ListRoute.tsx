import dayjs from 'dayjs';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GoPlus } from 'react-icons/go';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBtn,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import { formatEnabled } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import DeleteRoute from '../components/DeleteRoute';
import { ImportRoute } from '../components/ImportRoute';
import useAPI from '../useAPI/useAPI';
import { useRoute } from '../useAPI/useRoute';
import './ListRoute.scss';

const ListRoute = () => {
  const { t } = useTranslation();
  const [objSearch, setObjSearch] = useState({});
  const navigate = useNavigate();
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const [showDeleteRouteModal, setShowDeleteRouteModal] =
    useState<boolean>(false);

  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [showImportRouteModal, setShowImportRouteModal] =
    useState<boolean>(false);

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  const { getListRoutesAPI, activeRouteAPI, deactiveRouteAPI } = useAPI();
  const { importRoutes, exportRoute, deleteRoute } = useRoute();

  const HistoryBehaviorColumns = [
    {
      Header: 'ID',
      accessor: 'id',
    },
    {
      Header: 'Name',
      accessor: 'name',
    },
    {
      Header: 'Active',
      accessor: 'is_active',
      filterVariant: 'checkbox',
      filterOptions: ['True', 'False'],
      cell: (row: any) => formatEnabled(row?.row?.original?.is_active),
    },
    {
      Header: 'Created Date',
      accessor: 'created_on',
      filterVariant: 'datetime',
    },
    {
      Header: 'Total Stops',
      accessor: 'total_stops',
    },
    {
      Header: 'Start Point',
      accessor: 'start_point',
    },
    {
      Header: 'End Point',
      accessor: 'end_point',
    },
    {
      Header: 'Total Distance',
      accessor: 'total_distance',
    },
    {
      Header: 'Estimated Time',
      accessor: 'estimated_time',
    },
    {
      Header: 'Note',
      accessor: 'note',
    },
    {
      Header: t('In Use'),
      accessor: 'in_use',
      filterVariant: 'checkbox',
      filterOptions: ['True', 'False'],
      cell: (row: any) => formatEnabled(row?.row?.original?.in_use),
    },
  ];

  const handleGetListRoutes = useCallback(async () => {
    const { data, totalPage, totalItem } = await getListRoutesAPI({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearch,
    });

    setData({
      data: data,
      totalItem: totalItem,
      totalPage: totalPage,
    });
  }, [getListRoutesAPI, pageSize, currentPage, objSearch]);

  useEffect(() => {
    if (pageSize) {
      handleGetListRoutes();
    }
  }, [pageSize, currentPage, objSearch]);

  const handleSelectionRows = (selectedData: any) => {
    setSelectedRows(selectedData);
  };

  const handleViewDetailDevice = (selectedRow: any) => {
    navigate(`/routes/detail-route/${selectedRow.id}`, {
      state: { id: selectedRow.id },
    });
  };

  const handleActionRoute = useCallback(
    async (action: 'activate' | 'deactivate') => {
      const listId = selectedRows?.map((item) => item.id).join(',');
      const { success, message } = await (
        action === 'activate' ? activeRouteAPI : deactiveRouteAPI
      )({
        ids: listId,
        useLoading: true,
      });

      if (success) {
        const updatedData = data.data.map((item) => {
          const found = selectedRows.find((row) => row.id === item.id);
          if (found) {
            return {
              ...item,
              is_active: action === 'activate' ? true : false,
            };
          }
          return item;
        });

        setData({
          ...data,
          data: updatedData,
        });

        setRefreshTable(true);
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

  const handleExportRoute = async () => {
    const routeIds = selectedRows.map((item) => item.id);
    const { success, message } = await exportRoute({ route_ids: routeIds });

    if (success) {
      ToastTopHelper.success(message);
      setRefreshTable(true);
    } else {
      ToastTopHelper.error(message);
    }
  };

  const handleImportRoute = async (data: {
    files: File[];
    service: { value: number | string } | null;
  }) => {
    // create id by dayjs
    const id = Number(dayjs().format('YYYYMMDDHHmmss'));
    const {
      success,
      message,
      data: responseData,
    } = await importRoutes(data, id, () => {
      setRefreshTable(true);
      handleGetListRoutes();
    });

    if (success) {
      const accepted = responseData?.accepted || [];
      const rejected = responseData?.rejected || [];
      const acceptedCount = responseData?.accepted_count || 0;
      const rejectedCount = responseData?.rejected_count || 0;

      if (acceptedCount > 0 && rejectedCount === 0) {
        // All files imported successfully
        ToastTopHelper.success(
          t('Successfully imported {{count}} route(s).', {
            count: acceptedCount,
          }),
        );
      } else if (acceptedCount > 0 && rejectedCount > 0) {
        // Partial success
        const rejectedFileNames = rejected
          .map((r: any) => r.file_name)
          .join(', ');
        ToastTopHelper.warning(
          `${acceptedCount} route(s) imported successfully. ${rejectedCount} file(s) failed: ${rejectedFileNames}`,
        );
      } else {
        // All failed
        ToastTopHelper.error(message);
      }

      // Close modal only if at least one file was accepted
      if (acceptedCount > 0) {
        setShowImportRouteModal(false);
      }
    } else {
      ToastTopHelper.error(message);
    }
  };

  const disabledDeleteRoute = () => {
    if (selectedRows.length === 0) {
      return true;
    }
    if (selectedRows.some((item) => item.in_use)) {
      return true;
    }
    return false;
  };

  const handleDeleteRoute = async () => {
    const ids = selectedRows?.map((item) => item.id).join(',');
    const { success, message } = await deleteRoute(ids);
    if (success) {
      ToastTopHelper.success(message);
      handleGetListRoutes();
      setRefreshTable(true);
      setShowDeleteRouteModal(false);
    }
  };

  return (
    <Container
      id="list-device"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Import Route')}
            type="button"
            variant="outline"
            color="primary"
            actionType={ROLE_PERMISSION.READ}
            onClick={() => setShowImportRouteModal(true)}
          />,
          <CustomBtn
            label={t('Add New Route')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => navigate('/routes/add-new-route')}
          />,
        ]}
      />
      <Main>
        <div className="list-device__table-container">
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
                onClick={() => handleActionRoute('activate')}
              />,
              <CustomBtn
                label={t('Deactivate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionRoute('deactivate')}
              />,
              <CustomBtn
                label={t('Export')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.READ}
                disabled={selectedRows.length === 0}
                onClick={() => handleExportRoute()}
              />,
              <CustomBtn
                label={t('Delete')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.READ}
                disabled={disabledDeleteRoute()}
                onClick={() => setShowDeleteRouteModal(true)}
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
        {showImportRouteModal && (
          <ImportRoute
            showModal={showImportRouteModal}
            setHideModal={() => setShowImportRouteModal(false)}
            handleImportRoute={handleImportRoute}
          />
        )}
        {showDeleteRouteModal && (
          <DeleteRoute
            showModal={showDeleteRouteModal}
            setHideModal={() => setShowDeleteRouteModal(false)}
            onDelete={handleDeleteRoute}
          />
        )}
      </Main>
    </Container>
  );
};
export default ListRoute;
