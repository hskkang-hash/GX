import { yupResolver } from '@hookform/resolvers/yup';
import Timeline from '@mui/lab/Timeline';
import TimelineSeparator from '@mui/lab/TimelineSeparator';
import { Box } from '@mui/material';
import { useEffect, useMemo, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  CustomBreadcrumb,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
  FormBlock,
  Main,
  ToastTopHelper,
  useActivePayment,
  useTheme,
} from 'rj-core';

import ExpanDropDown from '@/components/Form/ExpanDropDown';
import { Tabs } from '@/components/Form/Tabs';
import CustomModal1 from '@/components/modal/CustomModal1';
import PaginationSelect from '@/components/selects/PaginationSelect';
import Colors from '@/configs/Colors';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import useBoolean from '@/hooks/useBoolean';
import { CustomRoutes } from '@/services/API';
import { schemaCancelOrder, schemaRefundCash } from '@/services/schemaForm';

import { getContrastTextColor } from '../../../../utils/utils';
import { CancelOrder } from '../components/CancelOrder';
import { ChangeStatus } from '../components/ChangeStatus';
import { DetailReceived } from '../components/DetailReceived';
import useAPI from '../useAPI';
import {
  formatStatusDeliveryInquiry,
  StatusAfterArrived,
} from '../utils/StatusColorInquiry';
import './DetailOrder.scss';
import OrderInfomation from './formsOrder/OrderInfomation';
import TrackingOrder from './formsOrder/TrackingOrder';
import {
  CustomTimelineConnector,
  CustomTimelineContent,
  CustomTimelineDot,
  CustomTimelineItem,
} from './style';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import { formatCurrency, useFormatCurrencyPlacement } from '@/utils/formatCurrency';
import { useFormatNumber } from '@/utils/formatConfig';

// Detail order status In Transit , Awating Delivery , Cancelled
const DetailOrder = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const activePayment = useActivePayment();
  const [dataDetail, setDataDetail] = useState<any>({});
  const [showModal, openModal, setHideModal] = useBoolean();
  const [activeTab, setActiveTab] = useState<number | undefined>(0);
  const [showModalCancelOrder, setShowModalCancelOrder] =
    useState<boolean>(false);
  const [showModalChangeStatus, setShowModalChangeStatus] =
    useState<boolean>(false);

  const orderDetailAwaitShipment = useMemo(
    () => dataDetail?.mapped_status_code === 'completed_order',
    [dataDetail],
  );

  const awaitingPaymentFail = useMemo(
    () =>
      dataDetail?.payment_status === 'failed' &&
      dataDetail?.mapped_status_code === 'completed_order',
    [dataDetail],
  );
  const [showModalRefund, setShowModalRefund] = useState<boolean>(false);
  const [showModalRefundCash, setShowModalRefundCash] =
    useState<boolean>(false);
  const { getDetailOrder, cancelOrder, refundCash, changeOrderStatus } =
    useAPI();
  const { pathname } = useLocation();
  const id = Number(pathname.split('/')[2]);
  const { converRawDateToDateTimeFormat } = useConvertDate();
  const fetchData = async () => {
    const { success, data, message } = await getDetailOrder(id);
    setDataDetail(data);
    if (!success) {
      ToastTopHelper.error(message);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const packageData = dataDetail?.items?.map((item: any) => ({
    id: item.id,
    price: item.amount,
    list_item: [
      {
        name: t('Weight'),
        value: (item?.weight?.value ?? 0) + ' ' + item?.weight?.unit,
      },
      {
        name: t('Dimensions'),
        value:
          item?.dimension_l?.value +
          item?.dimension_l?.unit +
          ' x ' +
          item?.dimension_w?.value +
          item?.dimension_w?.unit +
          ' x ' +
          item?.dimension_h?.value +
          item?.dimension_h?.unit,
      },
      {
        name: t('Item Type'),
        value: item?.item_type__name,
      },
      {
        name: t('Waterproof'),
        value: item?.is_waterproof && t('Yes'),
      },
      {
        name: t('Fragile'),
        value: item?.is_fragile && t('Yes'),
      },
      {
        name: t('Packaging'),
        value: item?.details,
      },
      {
        name: t('Note'),
        value: item?.note,
      },
    ],
  }));

  const { currencySymbol } = formatCurrency();
  const { formatNumber } = useFormatNumber();
  const { format: formatCurrencyPlacement } = useFormatCurrencyPlacement();
  const totalAmount = formatCurrencyPlacement(
    formatNumber(dataDetail?.financial_summary?.total_amount?.value),
    currencySymbol
  );
  const senderAndRecipientData = [
    {
      id: 1,
      title: t('Sender'),
      list_item: [
        {
          name: t('Name'),
          value: dataDetail?.sender_name,
        },
        {
          name: t('Phone Number'),
          value: dataDetail?.sender_phone,
        },
        {
          name: t('Pickup Location'),
          value: dataDetail?.origin,
        },
        {
          name: t('Note'),
          value: dataDetail?.sender_note,
        },
      ],
    },
    {
      id: 2,
      title: t('Recipient'),
      list_item: [
        {
          name: t('Name'),
          value: dataDetail?.recipient_name,
        },
        {
          name: t('Phone Number'),
          value: dataDetail?.recipient_phone,
        },
        {
          name: t('Pickup Location'),
          value: dataDetail?.recipient_address__full_address,
        },
        {
          name: t('Note'),
          value: dataDetail?.recipient_note,
        },
      ],
    },
    {
      id: 3,
      title: t('Delivery Option'),
      list_item: [
        {
          name: t('Location'),
          value:
            dataDetail?.delivery_option__code == 'delivery_to_door'
              ? dataDetail?.recipient_address__full_address
              : dataDetail?.destination,
        },
      ],
    },
  ];

  const orderDetail = useMemo(
    () => [
      { id: 1, name: 'Order ID', value: dataDetail?.order_code, label: 'all' },
      {
        id: 2,
        name: 'Status',
        styled: true,
        value: (
          <div
            style={{
              display: 'flex',
              gap: 8,
              width: 'fit-content',
              flexFlow: 'wrap',
            }}
          >
            {dataDetail?.mapped_status_list?.length > 0
              ? dataDetail?.mapped_status_list?.map(
                (item: {
                  name: string;
                  code: string;
                  background_color: string;
                  text_color: string;
                  border_color: string;
                }) =>
                  formatStatusDeliveryInquiry({
                    t,
                    status_name: item.name,
                    status_code: dataDetail?.mapped_status_code,
                    backgroundColor: item.background_color,
                    color: item.text_color,
                    border: item.border_color,
                    isShowButton: false,
                  }),
              )
              : dataDetail?.mapped_status_code &&
              formatStatusDeliveryInquiry({
                t,
                status_name: dataDetail?.mapped_status?.name,
                status_code: dataDetail?.mapped_status_code,
                backgroundColor: dataDetail?.mapped_status_background_color,
                color: getContrastTextColor(
                  dataDetail?.mapped_status_background_color,
                ),
                border: dataDetail?.mapped_status_border_color,
                isShowButton: false,
              })}
          </div>
        ),
        label: 'all',
      },
      {
        id: 3,
        name: 'Order Time',
        value: dataDetail?.created_on ? converRawDateToDateTimeFormat(dataDetail?.created_on) : '-',
        label: 'all',
      },
      {
        id: 3,
        name: 'Payment Time',
        value: dataDetail?.paid_time ? converRawDateToDateTimeFormat(dataDetail?.paid_time) : '-',
        label: 'payment_time',
      },
      {
        id: 4,
        name: 'Order Cancellation Time',
        value: dataDetail?.cancel_time ? converRawDateToDateTimeFormat(dataDetail?.cancel_time) : '-',
        label: 'cancelled',
      },
      {
        id: 5,
        name: 'Refund Time',
        value: dataDetail?.refunded_time ? converRawDateToDateTimeFormat(dataDetail?.refunded_time) : '-',
        label: 'cancelled',
      },
      {
        id: 6,
        name: 'Order Verification Time',
        value: dataDetail?.verified_time ? converRawDateToDateTimeFormat(dataDetail?.verified_time) : '-',
        label: 'order_verification',
      },
      {
        id: 7,
        name: 'Arrival Time',
        value: dataDetail?.arrived_time ? converRawDateToDateTimeFormat(dataDetail?.arrived_time) : '-',
        label: 'arrival_time',
      },
      {
        id: 8,
        name: 'Order Return Time',
        value: dataDetail?.returned_time ? converRawDateToDateTimeFormat(dataDetail?.returned_time) : '-',
        label: 'return_time',
      },
      {
        id: 9,
        name: 'Order Completion Time',
        value: dataDetail?.completed_time ? converRawDateToDateTimeFormat(dataDetail?.completed_time) : '-',
        label: 'completion_time',
      },
    ],
    [dataDetail], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const historyOrder = useMemo(
    () =>
      dataDetail?.history?.map((item: any, index: number) => {
        return {
          id: index + 1,
          date: item?.created_on ? converRawDateToDateTimeFormat(item?.created_on) : '-',
          description: item.description,
        };
      }),
    [dataDetail],
  );

  const getVisibleFields = (type: string) => {
    switch (type) {
      case 'pending_confirmation':
        return ['all', 'payment_time'];
      case 'cancelled':
      case 'receipt_cancelled':
        return ['all', 'payment_time', 'cancelled'];
      case 'pending_processing':
        return ['all', 'payment_time', 'order_verification'];
      case 'awaiting_payment':
        return ['all'];
      case 'awaiting_shipment':
        return ['all', 'payment_time', 'order_verification'];
      case 'awaiting_payment_fail':
        return ['all'];
      case 'returned':
        return [
          'all',
          'payment_time',
          'order_verification',
          'arrival_time',
          'return_time',
        ];
      case 'delivered':
        return [
          'all',
          'payment_time',
          'order_verification',
          'arrival_time',
          'completion_time',
        ];
      case 'received':
        return [''];
      default:
        return ['all'];
    }
  };

  const listTabs = [
    {
      label: t('Tracking Order'),
      content: <TrackingOrder dataDetail={dataDetail} />,
    },
    {
      label: t('Order Infomation'),
      content: <OrderInfomation dataDetail={dataDetail} />,
    },
  ];

  type PageType =
    | 'pending_confirmation'
    | 'cancelled'
    | 'pending_processing'
    | 'delivered'
    | 'returned'
    | 'awaiting_payment'
    | 'awaiting_payment_fail'
    | 'unverified_order'
    | 'verified_order'
    | 'completed_order'
    | 'receipt_cancelled';

  const pageType = useMemo(
    () => dataDetail?.mapped_status_code as PageType,
    [dataDetail],
  ); // eslint-disable-line react-hooks/exhaustive-deps
  const visibleLabels = getVisibleFields(pageType);
  const { getOptionsByModel } = useCommonAPI();

  const handleCancelOrder = async (reason: any, isReorder: boolean) => {
    if (!reason) {
      return null;
    }

    const { success, message, data } = await cancelOrder(id, reason);
    if (success) {
      if (data?.is_refund && data?.return_method == 'cash') {
        setShowModalRefundCash(true);
        setHideModal();
      } else {
        setShowModalRefund(true);
        setHideModal();
        ToastTopHelper.success(message);

        if (isReorder) {
          console.log('reorder', isReorder);
          console.log('reorder.....');
          navigate(
            CustomRoutes.deliveryInquiry.subRoutes.reOrder.path.replace(
              ':id',
              id.toString(),
            ),
          );
        } else {
          navigate(CustomRoutes.deliveryInquiry.path);
        }
      }
    } else {
      ToastTopHelper.error(message);
    }
  };
  const navigate = useNavigate();

  const [clickReorder, setClickReorder] = useState<boolean>(false);

  const handleRefundCashSubmit = async () => {
    const formData = watch();
    console.log({ formData });
    const payload = {
      refund_method: 'cash',
      bank_code: formData?.bank_name?.value?.value,
      account_number: formData?.account_number,
      account_holder_name: formData?.account_holder_name,
      reason: formData?.reason,
    };
    const { success, message, data } = await refundCash(id, payload);
    if (success) {
      if (clickReorder) {
        navigate(
          CustomRoutes.deliveryInquiry.subRoutes.reOrder.path.replace(
            ':id',
            id.toString(),
          ),
        );
      } else {
        navigate(CustomRoutes.deliveryInquiry.path);
      }
      ToastTopHelper.success(message);
    } else {
      ToastTopHelper.error(message);
    }
  };

  const methods = useForm({
    defaultValues: {
      reason: '',
      bank_name: { value: null },
      account_holder_name: '',
      account_number: '',
    },
    resolver: yupResolver(
      showModalRefundCash ? schemaRefundCash : schemaCancelOrder,
    ),
  });

  const {
    handleSubmit,
    control,
    setValue,
    reset,
    watch,
    formState: { isValid, isSubmitting },
  } = methods;

  const [loading, setLoading] = useState<boolean>(false);
  const handleSubmitModalCancelOrder = async (id: number, reason: string) => {
    setLoading(true);
    const { success, message } = await cancelOrder(id, reason);
    if (success) {
      ToastTopHelper.success(message);
      setShowModalCancelOrder(false);
      fetchData();
    } else {
      ToastTopHelper.error(message);
    }
    setLoading(false);
  };

  const [loadingChangeStatus, setLoadingChangeStatus] =
    useState<boolean>(false);
  const handleChangeStatus = async (id: number) => {
    setLoadingChangeStatus(true);
    const { success, message } = await changeOrderStatus(id);
    if (success) {
      ToastTopHelper.success(message);
      setShowModalChangeStatus(false);
      fetchData();
    } else {
      ToastTopHelper.error(message);
    }
    setLoadingChangeStatus(false);
  };
  const location = useLocation();
  const previousUrl = location.state?.previousUrl || '/delivery-inquiry';
  return (
    <>
      <FormProvider {...methods}>
        <form className="form-add-new-device">
          <CustomBreadcrumb
            items={[{ url: previousUrl }, { text: t('Order Detail') }]}
            buttons={
              pageType === 'verified_order'
                ? [
                  <CustomBtn
                    key="start-delivery"
                    label={t('Start Delivery')}
                    size="md"
                    type="button"
                    onClick={() => {
                      setShowModalChangeStatus(true);
                    }}
                  />,
                ]
                : pageType === 'unverified_order'
                  ? [
                    <CustomBtn
                      key="cancel-order"
                      label={t('Cancel Order')}
                      variant="outline"
                      color="secondary"
                      size="md"
                      type="button"
                      onClick={() => {
                        setShowModalCancelOrder(true);
                      }}
                    />,
                    <CustomBtn
                      key="start-delivery"
                      label={t('Start Delivery')}
                      size="md"
                      type="button"
                      onClick={() => {
                        setShowModalChangeStatus(true);
                      }}
                    />,
                  ]
                  : !StatusAfterArrived.includes(pageType)
                    ? [
                      <CustomBtn
                        key="cancel-order"
                        label={t('Cancel Order')}
                        variant="outline"
                        color="secondary"
                        size="md"
                        type="button"
                        onClick={() => {
                          setShowModalCancelOrder(true);
                        }}
                      />,
                    ]
                    : [
                      (pageType === 'pending_confirmation' ||
                        pageType === 'awaiting_payment' ||
                        pageType === 'awaiting_payment_fail') && (
                        <CustomBtn
                          key="cancel-order"
                          label={t('Cancel Order')}
                          variant="outline"
                          color="secondary"
                          size="md"
                          style={{
                            paddingLeft: '16px',
                            paddingRight: '16px',
                          }}
                          type="button"
                          onClick={openModal}
                        />
                      ),
                      awaitingPaymentFail && (
                        <CustomBtn
                          key="pay-again"
                          label={t('Pay Again')}
                          variant="contained"
                          color="primary"
                          size="md"
                          style={{
                            paddingLeft: '16px',
                            paddingRight: '16px',
                          }}
                          type="button"
                          onClick={() => alert('Navigate to Payment Page')}
                        />
                      ),
                      // (pageType === 'cancelled' ||
                      //   pageType === 'receipt_cancelled') && (
                      //   <CustomBtn
                      //     key="reorder"
                      //     label={t('Reorder')}
                      //     variant="outline"
                      //     color="secondary"
                      //     size="md"
                      //     style={{
                      //       paddingLeft: '16px',
                      //       paddingRight: '16px',
                      //     }}
                      //     type="button"
                      //     onClick={() =>
                      //       navigate(
                      //         CustomRoutes.deliveryInquiry.subRoutes.reOrder.path.replace(
                      //           ':id',
                      //           id.toString(),
                      //         ),
                      //       )
                      //     }
                      //   />
                      // ),
                    ]
            }
          />
          <Main>
            {pageType && (
              <>
                {pageType === 'unverified_order' ||
                  pageType === 'verified_order' ? (
                  <>
                    <DetailReceived
                      t={t}
                      theme={theme}
                      dataDetail={dataDetail}
                      totalAmount={totalAmount}
                    />
                  </>
                ) : (
                  <>
                    {!orderDetailAwaitShipment && (
                      <Box
                        sx={{
                          display: 'grid',
                          gap: '24px',
                          gridTemplateColumns: '8fr 4fr',
                          alignItems: 'start',
                        }}
                      >
                        {(pageType === 'cancelled' ||
                          pageType === 'receipt_cancelled') && (
                            <div className="grid-column-2">
                              <FormBlock
                                style={{
                                  backgroundColor:
                                    theme === 'dark' ? '#513D2B' : '#FBEBDD',
                                  color:
                                    theme === 'dark' ? '#ECECEF' : Colors.Gray7,
                                  padding: '8px 12px',
                                }}
                              >
                                <b>{t('Reason')}:</b> {dataDetail?.cancel_reason}
                              </FormBlock>
                            </div>
                          )}
                        {pageType === 'returned' && (
                          <div className="grid-column-2">
                            <FormBlock
                              style={{
                                backgroundColor:
                                  dataDetail?.message_type === 'error'
                                    ? theme === 'dark'
                                      ? '#613B3B'
                                      : '#FFEBE8'
                                    : theme === 'dark'
                                      ? '#513D2B'
                                      : '#FBEBDD',
                                color:
                                  dataDetail?.message_type === 'error'
                                    ? theme === 'dark'
                                      ? '#DF250B'
                                      : Colors.Red
                                    : theme === 'dark'
                                      ? '#ECECEF'
                                      : Colors.Gray7,
                                fontWeight:
                                  dataDetail?.message_type === 'error'
                                    ? 'bold'
                                    : 'normal',
                                padding: '8px 12px',
                              }}
                            >
                              {dataDetail?.message}
                            </FormBlock>
                          </div>
                        )}
                        <div
                          className="d-flex flex-column "
                          style={{ gap: '24px' }}
                        >
                          <FormBlock>
                            <Box
                              sx={{
                                display: 'grid',
                                gridTemplateColumns: '1fr 1fr',
                                columnGap: '24px',
                                rowGap: '8px',
                              }}
                            >
                              {orderDetail
                                .filter((item) =>
                                  visibleLabels.includes(item.label || 'all'),
                                )
                                .map((item) => {
                                  if (item?.value == null) return null;
                                  return (
                                    <Box
                                      key={item.id}
                                      sx={{
                                        display: 'grid',
                                        gridTemplateColumns: '1fr 1fr',
                                      }}
                                    >
                                      <div>{t(item.name)}</div>
                                      <span>{item.value}</span>
                                    </Box>
                                  );
                                })}
                            </Box>
                          </FormBlock>
                          <FormBlock>
                            <div
                              className="d-flex flex-column"
                              style={{ gap: '16px' }}
                            >
                              {senderAndRecipientData?.map((item, index) => (
                                <div
                                  key={item.id}
                                  style={{ padding: '3px' }}
                                >
                                  <div className="header-title pb-3">
                                    {t(item.title)}
                                  </div>
                                  <div className="d-flex flex-column gap-3">
                                    <ul
                                      className="d-flex flex-column rounded-3 list-unstyled"
                                      style={{
                                        backgroundColor:
                                          theme === 'dark'
                                            ? Colors.Gray7
                                            : '#F6F7F8',
                                        paddingLeft: '12px',
                                        paddingRight: '12px',
                                        marginBottom: 0,
                                      }}
                                    >
                                      {item.list_item
                                        .filter((i) => i.value != null)
                                        ?.map((listItem, listIndex) => (
                                          <li
                                            key={listIndex}
                                            style={{
                                              paddingTop: '8px',
                                              paddingBottom: '8px',
                                            }}
                                            className={`d-flex justify-content-between ${listIndex ===
                                              item.list_item.filter(
                                                (i) => i.value != null,
                                              ).length -
                                              1
                                              ? ''
                                              : 'border-bottom'
                                              }`}
                                          >
                                            <span>{listItem.name}</span>
                                            <span>{listItem.value}</span>
                                          </li>
                                        ))}
                                    </ul>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </FormBlock>
                        </div>
                        <div
                          className="d-flex flex-column"
                          style={{ gap: '24px' }}
                        >
                          <FormBlock>
                            <Box sx={{ height: 'fit-content' }}>
                              <div className="header-title pb-3">
                                {t('Invoice')}
                              </div>
                              {packageData?.map((item, index) => {
                                if (!item) return null;
                                if (!item.list_item) return null;
                                return (
                                  <div key={item.id}>
                                    <div className="d-flex flex-column gap-3">
                                      <div className="d-flex justify-content-between">
                                        <span>1 x {t('Package')}</span>
                                        <span>{formatCurrencyPlacement(
                                          formatNumber(item?.price),
                                          currencySymbol
                                        )}</span>
                                      </div>
                                      <ul
                                        style={{
                                          backgroundColor:
                                            theme === 'dark'
                                              ? Colors.Gray7
                                              : '#F6F7F8',
                                          padding: '10px',
                                          marginBottom: 0,
                                        }}
                                        className="d-flex flex-column gap-2 rounded-3 list-unstyled"
                                      >
                                        {item.list_item?.map((item, index) => {
                                          if (!item.value) return null;
                                          return (
                                            <li
                                              key={index}
                                              className="d-flex justify-content-between "
                                              style={{
                                                gap: '30px',
                                              }}
                                            >
                                              <span>{item.name}</span>
                                              <span>{String(item.value)}</span>
                                            </li>
                                          );
                                        })}
                                      </ul>
                                    </div>
                                    <hr
                                      hidden={
                                        !activePayment &&
                                        packageData.length - 1 === index
                                      }
                                      style={{ margin: '15px 0' }}
                                    />
                                  </div>
                                );
                              })}
                              {activePayment && (
                                <div
                                  style={{ gap: '6px' }}
                                  className="d-flex flex-column "
                                >
                                  <div className="d-flex justify-content-between header-title pb-0">
                                    <span>{t('Total')}</span>
                                    <span>
                                      {totalAmount}
                                    </span>
                                  </div>
                                  <div className="d-flex justify-content-between header-title pb-0">
                                    <span>{t('Payment Method')}</span>
                                    <span>
                                      {t(
                                        dataDetail?.payment_details
                                          ?.payment_method || '-',
                                      )}
                                    </span>
                                  </div>
                                </div>
                              )}
                            </Box>
                          </FormBlock>
                          {(pageType == 'returned' ||
                            pageType == 'delivered') && (
                              <ExpanDropDown
                                label={t('History')}
                                defaultExpanded={false}
                              >
                                <Timeline sx={{ padding: '10px 5px 2px' }}>
                                  {historyOrder?.map(
                                    (item: any, index: number) => (
                                      <CustomTimelineItem>
                                        <TimelineSeparator>
                                          <CustomTimelineDot />
                                          <CustomTimelineConnector />
                                        </TimelineSeparator>
                                        <CustomTimelineContent>
                                          <span style={{ color: Colors.Gray5 }}>
                                            {item.description}
                                          </span>
                                          <span
                                            style={{
                                              color:
                                                theme === 'dark'
                                                  ? Colors.Gray3
                                                  : Colors.Gray6,
                                            }}
                                          >
                                            {item.date}
                                          </span>
                                        </CustomTimelineContent>
                                      </CustomTimelineItem>
                                    ),
                                  )}
                                </Timeline>
                              </ExpanDropDown>
                            )}
                        </div>
                      </Box>
                    )}
                    {orderDetailAwaitShipment && (
                      <Tabs
                        items={listTabs}
                        activeTab={activeTab}
                        onTabChange={setActiveTab}
                      />
                    )}
                    {/* MODAL CANCEL ORDER */}
                    {(pageType == 'pending_confirmation' ||
                      pageType == 'awaiting_payment') && (
                        <CustomModal
                          title={t('Cancel Order')}
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
                                color:
                                  theme === 'dark' ? Colors.Gray4 : Colors.Gray6,
                              }}
                              className=""
                            >
                              {t(
                                "We'd love to know why you're cancelling—please share your reason.",
                              )}
                            </div>
                            <CustomInputHookForm
                              name="reason"
                              placeholder={t('Reason')}
                              control={control}
                            />
                          </div>
                          <ActionBtn
                            leftButtons={[
                              // Have'nt payment -> navigate to list order change status to Cancel
                              // Already payment online -> show modal Refund -> Close -> navifate to list order change status to Cancel
                              // Already payment by cash -> show modal Refund by cash -> Confirm -> navifate to list order change status to Cancel
                              <CustomBtn
                                type="button"
                                variant="contained"
                                color="primary"
                                size="lg"
                                disabled={!isValid}
                                label={t('Confirm')}
                                onClick={() => {
                                  handleCancelOrder(watch('reason'), false);
                                }}
                              />,
                            ]}
                            middleButtons={[
                              <CustomBtn
                                variant="outline"
                                type="button"
                                color="primary"
                                size="lg"
                                disabled={!isValid}
                                label={t('Confirm and Reorder')}
                                // if haven't payment -> navigate to add new order page and fill order information to all fields
                                // if already payment -> show moal refund/refund by cash -> Close/Confirm -> navigate to add new order page and fill order information to all fields
                                onClick={() => {
                                  setClickReorder(true);
                                  handleCancelOrder(watch('reason'), true);
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
                      )}
                    {/* REFUND */}
                    {/* ONLINE PAYMENT */}
                    {pageType == 'pending_confirmation' && showModalRefund && (
                      <CustomModal
                        title={t('Refund')}
                        closeButton={false}
                        show={showModalRefund}
                        onHide={() => setShowModalRefund(false)}
                      >
                        <div style={{ width: '45rem' }}>
                          <div
                            style={{
                              fontSize: '14px',
                              color:
                                theme === 'dark' ? Colors.Gray4 : Colors.Gray6,
                            }}
                            className=""
                          >
                            {' '}
                            {t(
                              'Your order has been cancelled and we will process your refund as soon as possible. Please allow 1–3 business days for the refund to be completed. If you have any questions, feel free to contact us for assistance',
                            )}
                          </div>
                        </div>
                        <ActionBtn
                          middleButtons={[
                            <CustomBtn
                              type="button"
                              variant="outline"
                              color="secondary"
                              size="lg"
                              onClick={() =>
                                navigate(CustomRoutes.deliveryInquiry.path)
                              }
                              label={t('Cancel')}
                            />,
                          ]}
                        />
                      </CustomModal>
                    )}

                    {/* CASH PAYMENT */}
                    {pageType == 'pending_confirmation' &&
                      showModalRefundCash && (
                        <CustomModal1
                          title={t('Refund')}
                          show={true}
                          closeButton={false}
                          onHide={() => {
                            setShowModalRefundCash(false);
                            reset();
                            setValue('bank_name', { value: null });
                            setValue('account_holder_name', '');
                            setValue('account_number', '');
                            setValue('reason', '');
                          }}
                        >
                          <div style={{ width: '65rem' }}>
                            <div
                              style={{
                                fontSize: '14px',
                                paddingBottom: '20px',
                                color:
                                  theme === 'dark'
                                    ? Colors.Gray4
                                    : Colors.Gray6,
                              }}
                              className=""
                            >
                              {t(
                                'Your order has been cancelled and we will process your refund as soon as possible. Since you paid by cash, the refund will be made via bank transfer. Please provide your bank account details and allow 1–3 business days for processing. If you have any questions, feel free to contact us for assistance.',
                              )}
                            </div>
                            <div className="form-grid">
                              <div className="grid-column-2">
                                <PaginationSelect
                                  required
                                  label={t('Bank Name')}
                                  name="bank_name.value"
                                  control={control}
                                  loadOptions={getOptionsByModel({
                                    name_modal: 'bank',
                                    key: 'name',
                                    value: 'code',
                                    search_field: 'name',
                                  })}
                                  placeholder={t('Select')}
                                />
                              </div>
                              <CustomInputHookForm
                                required
                                name="account_holder_name"
                                label={t('Account Holder Name')}
                                placeholder={t('Account Holder Name')}
                                control={control}
                              />
                              <CustomInputHookForm
                                required
                                name="account_number"
                                label={t('Account Number')}
                                placeholder={t('Account Number')}
                                control={control}
                              />
                            </div>
                          </div>
                          <ActionBtn
                            middleButtons={[
                              <CustomBtn
                                type="button"
                                variant="contained"
                                color="primary"
                                size="lg"
                                disabled={!isValid}
                                onClick={handleRefundCashSubmit}
                                label={t('Confirm')}
                              />,
                            ]}
                          />
                        </CustomModal1>
                      )}
                  </>
                )}
              </>
            )}
          </Main>
        </form>
      </FormProvider>

      <CancelOrder
        showModal={showModalCancelOrder}
        setHideModal={() => {
          setShowModalCancelOrder(false);
        }}
        handleCancelOrder={(reason: string) => {
          handleSubmitModalCancelOrder(id, reason);
        }}
        submitLoading={loading}
      />
      <ChangeStatus
        showModal={showModalChangeStatus}
        loading={loadingChangeStatus}
        setHideModal={() => {
          setShowModalChangeStatus(false);
        }}
        handleChangeStatus={() => {
          handleChangeStatus(id);
        }}
      />
    </>
  );
};

export default DetailOrder;
