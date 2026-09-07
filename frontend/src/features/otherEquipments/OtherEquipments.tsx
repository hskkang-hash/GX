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
import { failureLine } from '@/features/session/apiFailure';

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
    // ★ [SEC-11a ② · 2026-09-07 턴 J · 차선 C] **스피너를 끄는 것은 `finally` 다.**
    //   종전에는 마지막 줄의 `setLoading(false)` 하나가 전부였다. `await` 가 거절되면
    //   그 줄에 **닿지 못하고** 스피너가 그대로 남는다 — W0-18 §2-1 이 이름 붙인 모양이고,
    //   접두 승격이 켜지는 순간 실제로 그렇게 된다(200 봉투가 예외가 되므로).
    try {
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
    } catch (error) {
      // 거절을 **말한다.** 사전 문구다 — 여기서 문장을 짓지 않는다(GX-COPY 규칙 1).
      ToastTopHelper.error(failureLine('OtherEquipments.fetch', error));
    } finally {
      setLoading(false);
    }
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
      try {
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
      } catch (error) {
        // ★ [SEC-11a ② · 턴 J · 차선 C] 쓰기 단추가 **조용히 실패하지 않게** 한다.
        //   아무 말 없는 단추는 고장으로 읽히고, 사람은 한 번 더 누른다(P-78 ③).
        ToastTopHelper.error(failureLine('OtherEquipments.action', error));
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
