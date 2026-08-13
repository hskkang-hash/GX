import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
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

import SwitchBtn from '../../../components/Form/SwitchBtn';
import API, { endpoint } from '../../../services/API';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import { remToPx } from '../../../utils/utils';
import OffcanvasChecklistSettingForm from '../components/OffcanvasChecklistSettingForm';
import useChecklistSetting from '../hooks/useChecklistSetting';
import {
  ChecklistSettingPageReducer,
  initialChecklistSettingPageState,
} from '../store/checklistSetting.reducer';
import {
  BodyRequestChecklistSetting,
  ChecklistSettingFormValues,
  ChecklistSettingState,
  SettingCategoryState,
} from '../types/checklistSetting.types';

const CheckListSetting = () => {
  const { t } = useTranslation();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const isRoleSuperuser = CheckRoleAccount('superuser');

  const [objSearch, setObjSearch] = useState({});
  const {
    getChecklistSetting,
    createChecklistSetting,
    updateChecklistSetting,
    deleteChecklistSetting,
    getSettingCategory,
  } = useChecklistSetting();

  const [state, dispatch] = useReducer(
    ChecklistSettingPageReducer,
    initialChecklistSettingPageState,
  );

  const {
    pageSize,
    currentPage,
    selectedRows,
    refreshTable,
    openOffcanvas,
    data,
    offcanvasCreate,
    offcanvasEdit,
    selectedRow,
  } = state;

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  const handleGetData = useCallback(async () => {
    const {
      data: dataChecklistSetting,
      totalPage,
      totalItem,
    } = await getChecklistSetting({
      currentPage,
      pageSize: pageSize || 25,
      objSearch,
    });
    dispatch({
      type: 'SET_DATA',
      payload: { data: dataChecklistSetting, totalPage, totalItem },
    });
  }, [getChecklistSetting, dispatch, currentPage, pageSize, objSearch]);

  const handleCloseOffcanvas = useCallback(() => {
    dispatch({ type: 'SET_OFFCANVAS_CREATE', payload: false });
    dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: false });
    dispatch({ type: 'OPEN_OFFCANVAS', payload: false });
    dispatch({ type: 'SET_SELECTED_ROWS', payload: [] });
    dispatch({ type: 'SET_SELECTED_ROW', payload: null });
  }, []);

  const [isLoading, setIsLoading] = useState(false);
  const handleAddNewChecklistSetting = useCallback(
    async (values: ChecklistSettingFormValues) => {
      setIsLoading(true);
      let body: BodyRequestChecklistSetting = {
        item_name: values.item_name,
        category: values?.category as number,
      };

      if (isRoleSuperuser) {
        body = {
          ...body,
          group_id: values.group?.value,
        };
      }
      const { message, success } = await createChecklistSetting(body);

      if (success) {
        handleGetData();
        dispatch({ type: 'OPEN_OFFCANVAS', payload: false });
        dispatch({ type: 'SET_OFFCANVAS_CREATE', payload: false });
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
      setIsLoading(false);
    },
    [createChecklistSetting, handleGetData, isRoleSuperuser],
  );

  const handleUpdateChecklistSetting = useCallback(
    async (id: number, values: ChecklistSettingFormValues) => {
      setIsLoading(true);
      let body: BodyRequestChecklistSetting = {
        item_name: values.item_name,
        category: values?.category as number,
      };

      if (isRoleSuperuser) {
        body = {
          ...body,
          group_id: values.group?.value,
        };
      }
      const { message, success } = await updateChecklistSetting(id, body);

      if (success) {
        handleGetData();
        dispatch({ type: 'OPEN_OFFCANVAS', payload: false });
        dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: false });
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
      setIsLoading(false);
    },
    [updateChecklistSetting, handleGetData, isRoleSuperuser],
  );

  const handleDeleteChecklistSetting = useCallback(async () => {
    const ids = selectedRows?.map((row) => row.id).join(',');

    if (!ids) {
      ToastTopHelper.error(t('Please select at least one item'));
      return;
    }

    const { message, success } = await deleteChecklistSetting(ids);

    if (success) {
      handleGetData();
      ToastTopHelper.success(message);
      dispatch({ type: 'TOGGLE_REFRESH', payload: true });
      // Ensure offcanvas is properly closed after deletion
      dispatch({ type: 'SET_OFFCANVAS_CREATE', payload: false });
      dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: false });
      dispatch({ type: 'OPEN_OFFCANVAS', payload: false });
      dispatch({ type: 'SET_SELECTED_ROWS', payload: [] });
      dispatch({ type: 'SET_SELECTED_ROW', payload: null });
    } else {
      ToastTopHelper.error(message);
    }
  }, [deleteChecklistSetting, handleGetData, selectedRows, t]);

  useEffect(() => {
    (async () => {
      const response = await getSettingCategory();
      const convertOptions = response.map((item: SettingCategoryState) => ({
        value: item.name,
        label: item.name,
      }));
      dispatch({
        type: 'SET_SETTING_CATEGORY',
        payload: [
          {
            label: 'Select',
            value: '',
          },
          ...convertOptions,
        ],
      });
    })();
  }, []);

  useEffect(() => {
    if (pageSize) {
      handleGetData();
    }
  }, [pageSize, currentPage, objSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleClickRow = useCallback((row: ChecklistSettingState) => {
    dispatch({ type: 'SET_SELECTED_ROW', payload: row });
    dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: true });
    dispatch({ type: 'OPEN_OFFCANVAS', payload: true });
  }, []);

  const handleSelectedRows = useCallback((rows: ChecklistSettingState[]) => {
    dispatch({ type: 'SET_SELECTED_ROWS', payload: rows });
  }, []);

  // const columns = useMemo(() => {
  //   return [
  //     {
  //       Header: t('Category'),
  //       accessor: 'category_name',
  //       filterVariant: 'select',
  //       filterOptions: settingCategory.length > 0 ? settingCategory : [],
  //       cell: (row: any) => {
  //         return row.getValue() ? <span>{row.getValue()}</span> : null;
  //       },
  //     },
  //   ];
  // }, [t, settingCategory]);

  const toggleChecklistSetting = useCallback(
    async (id: number) => {
      const { message, success } = await API.put(
        endpoint.toggleChecklistSetting(id),
      );
      if (success) {
        handleGetData();
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [handleGetData],
  );

  const StatusCell = useCallback(({ info }: { info: any }) => {
    console.log('info_in_status_cell', info?.row?.original);
    return (
      <SwitchBtn
        actionType={ROLE_PERMISSION.UPDATE}
        statusValue={info?.row?.original?.is_active}
        onChange={() => {
          toggleChecklistSetting(info?.row?.original?.id);
        }}
      />
    );
  }, []);

  return (
    <Container
      id="list-checklist-setting"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            actionType={ROLE_PERMISSION.CREATE}
            label={t('Add New Item')}
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
          columns={[
            {
              Header: t('Active'),
              accessor: 'active',
              notUseConfigTable: true,
              enableSorting: true,
              enableColumnFilter: false,
              cell: (info: any) => <StatusCell info={info} />,
            },
          ]}
          data={data}
          objSearch={objSearch}
          setObjSearch={setObjSearch}
          onClickRow={handleClickRow}
          onSelectedRows={handleSelectedRows}
          refreshTable={refreshTable}
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
              onClick={handleDeleteChecklistSetting}
            />,
          ]}
          pageSize={pageSize}
          setPageSize={(size: number) => {
            dispatch({ type: 'SET_PAGE_SIZE', payload: size });
          }}
          offcanvas={openOffcanvas}
          setOpenOffcanvas={(boolean: boolean) => {
            dispatch({ type: 'OPEN_OFFCANVAS', payload: boolean });
            dispatch({ type: 'SET_OFFCANVAS_CREATE', payload: false });
            dispatch({ type: 'SET_OFFCANVAS_EDIT', payload: false });
          }}
        />
      </Main>
      {(offcanvasCreate || offcanvasEdit) && (
        <OffcanvasChecklistSettingForm
          show={offcanvasCreate || offcanvasEdit}
          onHide={handleCloseOffcanvas}
          id={`offcanvas-checklist-setting-${offcanvasCreate ? 'create' : `edit-${selectedRow?.id}`}`}
          initialValues={offcanvasEdit ? selectedRow : null}
          loading={isLoading}
          onSubmit={
            offcanvasCreate
              ? (values: ChecklistSettingFormValues) =>
                handleAddNewChecklistSetting(values)
              : (values: ChecklistSettingFormValues) =>
                handleUpdateChecklistSetting(values.id || 0, values)
          }
        />
      )}
    </Container>
  );
};

export default CheckListSetting;
