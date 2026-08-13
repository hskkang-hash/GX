import { t } from 'i18next';
import { useCallback, useEffect, useRef, useState } from 'react';
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

import { CustomRoutes } from '@/services/API';
import { formatEnabled } from '@/utils/formatColumns';
import { isEmptyObject, remToPx } from '@/utils/utils';

import useEquipment from './hooks/useEquipment';

const ListDevice = () => {
  const [objSearch, setObjSearch] = useState({});
  const navigate = useNavigate();
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const { getEquipmentList, activeEquipmentAPI, deactiveEquipmentAPI } =
    useEquipment();

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  const fetchOtherEquipments = async () => {
    setLoading(true);

    const { success, message, data, totalItem, totalPage } =
      await getEquipmentList({
        pageSize,
        currentPage,
        objSearch,
      });
    if (success) {
      setData({
        data: data,
        totalItem: totalItem,
        totalPage: totalPage,
      });
    } else {
      ToastTopHelper.error(message);
    }
    setLoading(false);
  };

  useEffect(() => {
    pageSize && !isEmptyObject(objSearch) && fetchOtherEquipments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageSize, currentPage, objSearch]);

  const handleSelectionRows = (selectedData) => {
    console.log(selectedData.id);
    setSelectedRows(selectedData);
  };

  const handleActionEquipment = useCallback(
    async (action: 'activate' | 'deactivate') => {
      const listId = selectedRows?.map((item) => item.id).join(',');
      const { success, message } = await (
        action === 'activate' ? activeEquipmentAPI : deactiveEquipmentAPI
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

  const handleViewDetailEquipment = (selectedRow) => {
    if (selectedRow.id && selectedRow.active) {
      navigate(
        CustomRoutes.otherEquipments.subRoutes.detailEquipment.path.replace(
          ':id',
          selectedRow.id.toString(),
        ),
      );
    }
  };

  const headerPageRef = useRef(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  const handleAddNewOtherEquipment = () => {
    navigate(CustomRoutes.otherEquipments.subRoutes.addNewOtherEquipment.path);
  };

  return (
    <Container
      id="list-other-equipments"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Add Equipment')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={handleAddNewOtherEquipment}
          />,
        ]}
      />

      <Main>
        <div className="list-device__table-container">
          <CustomizableTable
            stickyHeader
            availableHeight={spaceTableHeight}
            columns={[
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
            ]}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleViewDetailEquipment}
            onSelectedRows={handleSelectionRows}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            pageSize={pageSize}
            setPageSize={setPageSize}
            buttons={[
              <CustomBtn
                label={t('Activate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionEquipment('activate')}
              />,
              <CustomBtn
                label={t('Deactivate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionEquipment('deactivate')}
              />,
            ]}
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
export default ListDevice;
