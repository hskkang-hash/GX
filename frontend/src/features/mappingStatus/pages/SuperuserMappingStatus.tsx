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
import OffcanvasOrderStatusForm from '../components/OffcanvasMappingStatusForm';
import useMappingStatus from '../hooks/useMappingStatus';
import {
  MappingStatusPageReducer,
  initialMappingStatusState,
} from '../store/mappingStatus.reducer';
import {
  MappingStatusFormValues,
  MappingStatusResponse,
} from '../types/mappingStatus.types';

const SuperuserMappingStatus = () => {
  const { t } = useTranslation();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  const [objSearch, setObjSearch] = useState({});
  const {
    getListMappingStatus,
    createMappingStatus,
    updateMappingStatus,
    deleteMappingStatus,
  } = useMappingStatus();

  const [state, dispatch] = useReducer(
    MappingStatusPageReducer,
    initialMappingStatusState,
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

  const columns = useMemo(() => {
    return [];
  }, []);

  const handleClickRow = useCallback((row: MappingStatusResponse) => {
    dispatch({
      type: 'SET_SELECTED_ROW',
      payload: {
        id: row.id,
        group__id: row.group__id,
        group__name: row.group__name,
      },
    });
    dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: true });
    dispatch({ type: 'OPEN_OFFCANVAS', payload: true });
  }, []);

  const handleSelectedRows = useCallback((rows: MappingStatusResponse[]) => {
    dispatch({
      type: 'SET_SELECTED_ROWS',
      payload: rows.map((row) => ({
        id: row.id,
        group__id: row.group__id,
        group__name: row.group__name,
      })),
    });
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
    } = await getListMappingStatus({
      currentPage,
      pageSize: pageSize || 25,
      objSearch,
    });
    dispatch({
      type: 'SET_DATA',
      payload: { data: dataOrderStatus, totalPage, totalItem },
    });
  }, [getListMappingStatus, dispatch, currentPage, pageSize, objSearch]);

  const handleAddNewMappingStatus = useCallback(
    async (values: MappingStatusFormValues) => {
      const { message, success } = await createMappingStatus(values);

      if (success) {
        handleGetData();
        dispatch({ type: 'OPEN_OFFCANVAS', payload: false });
        dispatch({ type: 'SET_OFFCANVAS_CREATE', payload: false });
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [createMappingStatus, handleGetData],
  );

  const handleUpdateMappingStatus = useCallback(
    async (id: number, values: MappingStatusFormValues) => {
      const { message, success } = await updateMappingStatus(id, values);

      if (success) {
        handleGetData();
        dispatch({ type: 'OPEN_OFFCANVAS', payload: false });
        dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: false });
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [updateMappingStatus, handleGetData],
  );

  const handleDeleteMappingStatus = useCallback(async () => {
    const ids = selectedRows?.map((row) => row.group__id).join(',');

    if (!ids) {
      ToastTopHelper.error(t('Please select at least one item'));
      return;
    }

    const { message, success } = await deleteMappingStatus(ids);

    if (success) {
      handleGetData();
      ToastTopHelper.success(message);
      dispatch({ type: 'TOGGLE_REFRESH', payload: true });
    } else {
      ToastTopHelper.error(message);
    }
  }, [deleteMappingStatus, handleGetData, selectedRows, t]);

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
            label={t('Add New Mapping')}
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
              onClick={handleDeleteMappingStatus}
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
          listIdGroup={data?.data?.map((item) => item.group__id) || []}
          onSubmit={
            offcanvasCreate
              ? (values: MappingStatusFormValues) =>
                  handleAddNewMappingStatus(values)
              : (values: MappingStatusFormValues) =>
                  handleUpdateMappingStatus(values.group_id || 0, values)
          }
        />
      )}
    </Container>
  );
};

export default SuperuserMappingStatus;
