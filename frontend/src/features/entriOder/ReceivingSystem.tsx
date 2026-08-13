import { theme as antdTheme, ConfigProvider, Input, Select } from 'antd';
import { useEffect, useMemo, useRef, useState } from 'react';
// import { FormProvider } from "antd/es/form/context";
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { GoPlus } from 'react-icons/go';
import { useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  Container,
  CustomBtn,
  CustomInputHookForm,
  CustomizableTable,
  CustomModal,
  HeaderWithBtn,
  Main,
  ROLE_PERMISSION,
  SearchCard,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
  useUserInfo,
} from 'rj-core';

import Colors from '@/configs/Colors';
import useBoolean from '@/hooks/useBoolean';
import { CustomRoutes } from '@/services/API';
import { formatStatusEtri } from '@/utils/formatColumns';
import { isEmptyObject, remToPx } from '@/utils/utils';

import i18n from '../../i18n';
import { useDateTimeFormat } from '../Handover/hooks/useDateFormat';
import { formatDateTime } from '../Handover/utils/dateFormat';
import './assets/scss/ReceivingSystem.scss';
import SubComponentTable from './components/SubComponentTable';
import useAPI from './hooks/useAPI';

interface ListData {
  data: any[];
  totalItem: number;
  totalPage: number;
}

interface OrderStatus {
  label: string;
  value: string;
}

const ReceivingSystem = () => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const navigate = useNavigate();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const searchCardRef = useRef<HTMLDivElement>(null);
  const [statusList, setStatusList] = useState<string>('');
  const [receiptCode, setReceiptCode] = useState<string>('');
  const [objSearch, setObjSearch] = useState<any>({});
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>();
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [showModal, openModal, setHideModal] = useBoolean();
  const [data, setData] = useState<ListData>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });
  const userInfo = useUserInfo();
  const isSuperuser = useMemo(
    () => userInfo?.roles?.some((role: any) => role.code === 'superuser'),
    [userInfo],
  );
  const [orderStatus, setOrderStatus] = useState<OrderStatus[]>([
    {
      label: t('All'),
      value: '',
    },
  ]);

  const { getListOrderDetail, getDetailOrder, getOrderStatus } = useAPI();
  const { dateFormat, timeFormat, timezoneCode } = useDateTimeFormat();
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchCardRef],
    additionalHeights: [remToPx(8)],
  });

  const MENU_RECEIVING_SYSTEM_COLUMNS = useMemo(
    () => [
      {
        Header: 'Receipt Number',
        accessor: 'another_info.etri.receipt_id',
        enableColumnFilter: false,
        enableSorting: false,
        customStyle: {
          verticalAlign: 'top',
        },
      },
      {
        Header: 'Tracking Number',
        accessor: 'another_info.etri.tracking_number',
        enableColumnFilter: false,
        enableSorting: false,
      },
      {
        Header: 'Status',
        accessor: 'mapped_status',
        enableColumnFilter: false,
        cell: (row: any) => {
          return <>{formatStatusEtri(row?.row?.original?.mapped_status, t)}</>;
        },
      },
      {
        Header: 'Reason for Rejection',
        accessor: 'cancel_reason',
        enableColumnFilter: false,
        enableSorting: false,
      },
      {
        Header: 'Date Received',
        accessor: 'created_on',
        enableColumnFilter: false,
        enableSorting: false,
        filterVariant: 'datetime',
      },
      {
        Header: 'Delivery/Cancel Date',
        accessor: 'delivery_completion_date_time',
        enableColumnFilter: false,
        enableSorting: false,
        filterVariant: 'datetime',
      },
      {
        Header: 'entri_order.Sender',
        accessor: 'sender_name',
        enableColumnFilter: false,
        enableSorting: false,
      },
      {
        Header: 'entri_order.Sender Address',
        accessor: 'sender_address__full_address',
        enableColumnFilter: false,
        enableSorting: false,
      },
      {
        Header: 'entri_order.Recipient',
        accessor: 'recipient_name',
        enableColumnFilter: false,
        enableSorting: false,
      },
      {
        Header: 'entri_order.Recipient Address',
        accessor: 'recipient_address__full_address',
        enableColumnFilter: false,
        enableSorting: false,
      },
    ],
    [dateFormat, t, timeFormat],
  );

  useEffect(() => {
    handleGetOrderStatus();
  }, []);

  useEffect(() => {
    if (pageSize && !isEmptyObject(objSearch)) {
      handleGetListOrder();
    }
  }, [currentPage, pageSize, objSearch]);

  const handleGetListOrder = async () => {
    const { success, data, message } = await getListOrderDetail({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearch,
    });

    if (success) {
      setData(data);
    } else {
      ToastTopHelper.error(message);
    }
  };

  const handleGetOrderStatus = async () => {
    const { success, data, message } = await getOrderStatus();
    if (success) {
      setOrderStatus([...orderStatus, ...data]);
    } else {
      ToastTopHelper.error(message);
    }
  };

  const methods = useForm({
    defaultValues: {
      reason: t('사용자 취소'),
    },
  });

  const { control, setValue, reset, watch } = methods;

  const { cancelOrder } = useAPI();

  const handleCancelOrder = async (reason: any) => {
    if (!reason && !activeOrderId) {
      return null;
    }

    const { success, message, data } = await cancelOrder(activeOrderId, reason);

    if (success) {
      ToastTopHelper.success(message);
      setActiveCancelOrder(false);
      setActiveOrderId(undefined);
      setHideModal();
      setRefreshTable((prev) => !prev);
      handleGetListOrder();
      reset();
      // navigate(CustomRoutes.etriOrder.path);
    }
    if (!success) {
      ToastTopHelper.error(message);
    }
  };

  const prefixConditionsAfter = () => {
    return (
      <ConfigProvider
        theme={{
          algorithm:
            theme === 'dark'
              ? antdTheme.darkAlgorithm
              : antdTheme.defaultAlgorithm,
        }}
      >
        <div
          className="d-flex align-items-center gap-2"
          style={{
            padding: '0.125rem 0',
            borderRight:
              theme === 'dark' ? '1.5px solid #444646' : '1.5px solid #dee2e6',
          }}
        >
          <label className="fw-semibold d-block">{t('Status')}</label>

          <Select
            defaultValue={''}
            onChange={(value) => {
              setStatusList(value);
            }}
            classNames={{
              root: `custom-select-root ${theme === 'dark' ? 'dark-select' : 'light-select'}`,
            }}
            styles={{
              root: {
                minWidth: 170,
                color: theme === 'dark' ? '#fff' : '#000',
                height: '2.419rem',
                fontSize: '0.875rem',
              },
              popup: {
                root: {
                  backgroundColor: theme === 'dark' ? '#212529' : '#fff',
                },
              },
            }}
            options={orderStatus}
          />

          <label
            className=" fw-semibold d-block"
            style={{
              textWrap: 'nowrap',
            }}
          >
            {t('Receipt Number or Tracking Number')}
          </label>

          <Input
            style={{
              color: theme === 'dark' ? '#fff' : '#000',
              backgroundColor: theme === 'dark' ? '#212529' : '#fff',
              transition: 'unset',
              minWidth: 200,
              height: '2.419rem',
              fontSize: '0.875rem',
            }}
            className="me-3"
            placeholder={t('Receipt Number or Tracking Number')}
            onChange={(e) => {
              setReceiptCode(e.target.value);
            }}
          />
        </div>
      </ConfigProvider>
    );
  };

  const handleGetOrderDetail = async (id: number) => {
    const { success, data: detailData, message } = await getDetailOrder(id);
    if (success) {
      return detailData;
    } else {
      ToastTopHelper.error(message);
      return [];
    }
  };

  const handleClickSearch = (dateTime: {
    startDate: string;
    endDate: string;
  }) => {
    setExpanded({});
    setCurrentPage(1);
    setObjSearch((prevState: any) => ({
      ...prevState,
      startDate: dateTime?.startDate || null,
      endDate: dateTime?.endDate || null,
      mapped_status: statusList || null,
      receipt_code: receiptCode || null,
    }));
  };
  const [activeCancelOrder, setActiveCancelOrder] = useState<boolean>(false);
  const [activeOrderId, setActiveOrderId] = useState<number | undefined>();

  const handleClickRow = async (dataRow: any, row: any) => {
    const rowId = dataRow?.id;
    const isCurrentlyExpanded = row?.getIsExpanded();

    if (isCurrentlyExpanded) {
      setActiveCancelOrder(false);
      setActiveOrderId(undefined);
      setExpanded((prevState) => {
        const currentlyExpandedId = Object.keys(prevState)[0];
        const isSameRow = currentlyExpandedId === rowId;
        if (isSameRow) {
          return {};
        }
        return { [row.id]: true };
      });
      row.toggleExpanded(false);
      return;
    }

    if (dataRow.mapped_status === t('etri.Receipt Completed')) {
      setActiveCancelOrder(true);
      setActiveOrderId(dataRow?.id);
    } else {
      setActiveCancelOrder(false);
    }
    if (
      !data.data.find((item: { id: number }) => item?.id === rowId)?.subRows
    ) {
      const detailData = await handleGetOrderDetail(rowId);
      const convertDetailData = {
        ...detailData,
        completed_date: detailData?.completed_time
          ? formatDateTime(
              detailData?.completed_time,
              dateFormat,
              timeFormat,
              i18n.language,
              timezoneCode,
            )
          : '-',
        delivered_time: detailData?.delivered_time
          ? formatDateTime(
              detailData?.delivered_time,
              dateFormat,
              timeFormat,
              i18n.language,
              timezoneCode,
            )
          : '-',
        cancel_time: detailData?.cancel_time
          ? formatDateTime(
              detailData?.cancel_time,
              dateFormat,
              timeFormat,
              i18n.language,
              timezoneCode,
            )
          : '-',
      };
      setData((prevState) => ({
        ...prevState,
        data: prevState.data.map((item) =>
          item.id === rowId ? { ...item, subRows: convertDetailData } : item,
        ),
      }));
    }

    setExpanded((prevState) => {
      const currentlyExpandedId = Object.keys(prevState)[0];
      const isSameRow = currentlyExpandedId === rowId;
      if (isSameRow) {
        return {};
      }
      return { [row.id]: true };
    });

    row.toggleExpanded(true);
  };

  return (
    <Container id="list-receiving-system">
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Add New Order')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => {
              isSuperuser
                ? ToastTopHelper.warning(
                    t(
                      'System accounts cannot create orders. Please log in with a member account to use this feature.',
                    ),
                  )
                : navigate(
                    CustomRoutes.etriOrder.subRoutes.addNewEtriOrder.path,
                  );
            }}
          />,
          <CustomBtn
            variant="contained"
            className="btn-cancel-order"
            label={t('entri_order.cancel_order')}
            style={{ display: activeCancelOrder ? 'block' : 'none' }}
            onClick={openModal}
          />,
        ]}
      />
      <Main>
        <SearchCard
          ref={searchCardRef}
          hideAdvancedSearch
          hideClean
          hideTimeHelper
          title={t('Date Received')}
          prefixConditionsAfter={prefixConditionsAfter}
          setObjSearch={setObjSearch}
          objSearch={objSearch}
          handleClickSearch={handleClickSearch}
        />
        <CustomizableTable
          stickyHeader
          useActiveRowBorder
          availableHeight={spaceTableHeight}
          columns={MENU_RECEIVING_SYSTEM_COLUMNS}
          data={data}
          onClickRow={handleClickRow}
          renderSubComponent={SubComponentTable}
          hasSubComponent={true}
          expanded={expanded}
          setExpanded={setExpanded}
          objSearch={objSearch}
          setObjSearch={setObjSearch}
          useSystemSetting
          subTable
          notShowSelectRow
          refreshTable={refreshTable}
          setRefreshTable={setRefreshTable}
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          pageSize={pageSize}
          setPageSize={setPageSize}
        />
        <FormProvider {...methods}>
          <form>
            <CustomModal
              title={t('entri_order.cancel_order')}
              show={showModal}
              onHide={() => {
                setValue('reason', '');
                setHideModal();
              }}
            >
              <div style={{ width: '45rem' }}>
                <div
                  style={{
                    fontSize: '14px',
                    paddingBottom: '20px',
                    color: theme === 'dark' ? Colors.Gray4 : Colors.Gray6,
                  }}
                  className=""
                >
                  {t(
                    "We'd love to know why you're cancelling—please share your reason.",
                  )}
                </div>
                <CustomInputHookForm
                  name="reason"
                  placeholder={t('Reason-Etri')}
                  control={control}
                />
              </div>
              <ActionBtn
                styles={{ maxWidth: '100%' }}
                leftButtons={[
                  <CustomBtn
                    type="button"
                    variant="contained"
                    color="primary"
                    size="lg"
                    disabled={watch('reason') === ''}
                    label={t('Confirm')}
                    onClick={() => {
                      handleCancelOrder(watch('reason'));
                    }}
                  />,
                ]}
                rightButtons={[
                  <CustomBtn
                    type="button"
                    variant="outline"
                    color="secondary"
                    size="lg"
                    onClick={() => {
                      setHideModal();
                      reset();
                    }}
                    label={t('Cancel')}
                  />,
                ]}
              />
            </CustomModal>
          </form>
        </FormProvider>
      </Main>
    </Container>
  );
};

export default ReceivingSystem;
