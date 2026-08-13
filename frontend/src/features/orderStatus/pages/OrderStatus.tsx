import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { GoPlus } from 'react-icons/go';
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

import { remToPx } from '../../../utils/utils';
import OffcanvasOrderStatusForm from '../components/OffcanvasOrderStatusForm';
import useOrderStatus from '../hooks/useOrderStatus';
import {
  OrderStatusPageReducer,
  initialOrderStatusState,
} from '../store/orderStatus.reducer';
import {
  OrderStatusFormValues,
  OrderStatusState,
} from '../types/orderStatus.types';

const OrderStatus = () => {
  const { t } = useTranslation();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  const [objSearch, setObjSearch] = useState({});
  const {
    getListOrderStatus,
    createOrderStatus,
    updateOrderStatus,
    deleteOrderStatus,
  } = useOrderStatus();

  const [state, dispatch] = useReducer(
    OrderStatusPageReducer,
    initialOrderStatusState,
  );

  const {
    pageSize,
    currentPage,
    selectedRows,
    selectedRow,
    refreshTable,
    openOffcanvas,
    offcanvasCreate,
    offcanvasEdit,
    data,
  } = state;

  const columns = useMemo(
    () => [
      {
        Header: t('Text Color'),
        accessor: 'text_color',
        enableSorting: false,
        enableColumnFilter: false,
        cell: (row: { row: { original: { text_color: string } } }) => {
          return row?.row?.original?.text_color ? (
            <div
              style={{
                height: 16,
                width: 30,
                backgroundColor: row?.row?.original?.text_color,
                borderRadius: 4,
                border: '1px solid #DDDFE2',
              }}
            ></div>
          ) : null;
        },
      },
      {
        Header: t('Background Color'),
        accessor: 'background_color',
        enableSorting: false,
        enableColumnFilter: false,
        cell: (row: { row: { original: { background_color: string } } }) => {
          return row?.row?.original?.background_color ? (
            <div
              style={{
                height: 16,
                width: 30,
                backgroundColor: row?.row?.original?.background_color,
                borderRadius: 4,
                border: '1px solid #DDDFE2',
              }}
            ></div>
          ) : null;
        },
      },
      {
        Header: t('Border Color'),
        accessor: 'border_color',
        enableSorting: false,
        enableColumnFilter: false,
        cell: (row: { row: { original: { border_color: string } } }) => {
          return row?.row?.original?.border_color ? (
            <div
              style={{
                height: 16,
                width: 30,
                backgroundColor: row?.row?.original?.border_color,
                borderRadius: 4,
                border: '1px solid #DDDFE2',
              }}
            ></div>
          ) : null;
        },
      },
    ],
    [t],
  );

  const handleClickRow = useCallback((row: OrderStatusState) => {
    dispatch({ type: 'SET_SELECTED_ROW', payload: row });
    dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: true });
    dispatch({ type: 'OPEN_OFFCANVAS', payload: true });
  }, []);

  const handleSelectedRows = useCallback((rows: OrderStatusState[]) => {
    dispatch({ type: 'SET_SELECTED_ROWS', payload: rows });
  }, []);

  const handleCloseOffcanvas = useCallback(() => {
    dispatch({ type: 'SET_OFFCANVAS_CREATE', payload: false });
    dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: false });
    dispatch({ type: 'OPEN_OFFCANVAS', payload: false });
    dispatch({ type: 'SET_SELECTED_ROW', payload: null });
  }, []);

  const handleGetData = useCallback(async () => {
    const {
      data: dataOrderStatus,
      totalPage,
      totalItem,
    } = await getListOrderStatus({
      currentPage,
      pageSize: pageSize || 25,
      objSearch,
    });
    dispatch({
      type: 'SET_DATA',
      payload: { data: dataOrderStatus, totalPage, totalItem },
    });
  }, [getListOrderStatus, dispatch, currentPage, pageSize, objSearch]);

  const handleAddNewOrderStatus = useCallback(
    async (values: OrderStatusFormValues) => {
      const { message, success } = await createOrderStatus(values);

      if (success) {
        handleGetData();
        dispatch({ type: 'OPEN_OFFCANVAS', payload: false });
        dispatch({ type: 'SET_OFFCANVAS_CREATE', payload: false });
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [createOrderStatus, handleGetData],
  );

  const handleUpdateOrderStatus = useCallback(
    async (id: number, values: OrderStatusFormValues) => {
      const { message, success } = await updateOrderStatus(id, {
        name: values.name,
        value: values.value,
        text_color: values.text_color,
        background_color: values.background_color,
        border_color: values.border_color,
        group_id: values.group_id,
      });

      if (success) {
        handleGetData();
        dispatch({ type: 'OPEN_OFFCANVAS', payload: false });
        dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: false });
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [updateOrderStatus, handleGetData],
  );

  const handleDeleteOrderStatus = useCallback(async () => {
    const ids = selectedRows?.map((row) => row.id).join(',');

    if (!ids) {
      ToastTopHelper.error(t('Please select at least one item'));
      return;
    }

    const { message, success } = await deleteOrderStatus(ids);

    if (success) {
      handleGetData();
      ToastTopHelper.success(message);
      dispatch({ type: 'TOGGLE_REFRESH', payload: true });
    } else {
      ToastTopHelper.error(message);
    }
  }, [deleteOrderStatus, handleGetData, selectedRows, t]);

  useEffect(() => {
    if (pageSize) {
      handleGetData();
    }
  }, [pageSize, currentPage, objSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Container
      id="list-order-status"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            actionType={ROLE_PERMISSION.CREATE}
            label={t('Add New Status')}
            icon={<GoPlus size={18} />}
            onClick={() => {
              dispatch({ type: 'SET_OFFCANVAS_CREATE', payload: true });
              dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: false });
              dispatch({ type: 'OPEN_OFFCANVAS', payload: true });
            }}
          />,
        ]}
      />
      <Main>
        <CustomizableTable
          stickyHeader
          availableHeight={spaceTableHeight}
          columns={columns}
          data={data}
          objSearch={objSearch}
          setObjSearch={setObjSearch}
          onClickRow={handleClickRow}
          onSelectedRows={handleSelectedRows}
          refreshTable={refreshTable}
          pageSize={pageSize}
          setPageSize={(size: number) => {
            dispatch({ type: 'SET_PAGE_SIZE', payload: size });
          }}
          setRefreshTable={(refresh: boolean) => {
            dispatch({ type: 'TOGGLE_REFRESH', payload: refresh });
          }}
          currentPage={currentPage}
          setCurrentPage={(page: number) => {
            dispatch({ type: 'SET_CURRENT_PAGE', payload: page });
          }}
          buttons={[
            <CustomBtn
              label={t('Delete')}
              type="button"
              variant="outline"
              color="primary"
              size="sm"
              actionType={ROLE_PERMISSION.DELETE}
              disabled={selectedRows?.length === 0}
              onClick={handleDeleteOrderStatus}
            />,
          ]}
          offcanvas={openOffcanvas}
          setOpenOffcanvas={(boolean: boolean) => {
            dispatch({ type: 'OPEN_OFFCANVAS', payload: boolean });
            dispatch({ type: 'SET_OFFCANVAS_CREATE', payload: false });
            dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: false });
          }}
        />
      </Main>
      {(offcanvasCreate || offcanvasEdit) && (
        <OffcanvasOrderStatusForm
          show={offcanvasCreate || offcanvasEdit}
          onHide={handleCloseOffcanvas}
          id={`offcanvas-order-status-${offcanvasCreate ? 'create' : `edit-${selectedRow?.id}`}`}
          initialValues={offcanvasEdit ? selectedRow : null}
          onSubmit={
            offcanvasCreate
              ? (values: OrderStatusFormValues) =>
                  handleAddNewOrderStatus(values)
              : (values: OrderStatusFormValues) =>
                  handleUpdateOrderStatus(values.id || 0, values)
          }
        />
      )}
    </Container>
  );
};

export default OrderStatus;
