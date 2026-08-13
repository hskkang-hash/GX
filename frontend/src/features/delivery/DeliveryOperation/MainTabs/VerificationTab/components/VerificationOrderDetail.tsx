import { Box, Typography } from '@mui/material';
import { useRef, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import { useNavigate } from 'react-router-dom';
import { useReactToPrint } from 'react-to-print';
import {
  ActionBtn,
  CenterBtn,
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
import PaginationSelect from '@/components/selects/PaginationSelect';
import Colors, {
  border,
  colorOpacity,
  infoBg,
  textLabel,
  textValue,
} from '@/configs/Colors';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import NunjucksRenderer from '@/features/waybillTemplate/components/NunjucksRenderer';
import { replaceQRParagraphWithDiv } from '@/features/waybillTemplate/hooks/convertFields';
import API, { CustomRoutes, endpoint } from '@/services/API';
import { generateStyledQRCode } from '@/utils/generateStyledQRCode';

import { getContrastTextColor } from '../../../../../../utils/utils';
import { formatStatusDeliveryInquiry } from '../../../../deliveryInquiry/utils/StatusColorInquiry';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import { useFormatNumber } from '@/utils/formatConfig';
import { formatCurrency, useFormatCurrencyPlacement } from '@/utils/formatCurrency';

async function addQRCodeToData(data: any): Promise<any> {
  const qrUrl = Array.isArray(data.qr_code) ? data.qr_code[0] : data.qr_code;
  let qr_code_img = '';

  if (qrUrl) {
    const primaryColor =
      getComputedStyle(document.documentElement)
        .getPropertyValue('--ga-primary')
        .trim() || '#2196f3';

    const url_qr_code =
      import.meta.env.VITE_API_URL_FE +
      CustomRoutes.qrCode +
      `?dataQRCode=${encodeURIComponent(JSON.stringify(qrUrl))}`;

    qr_code_img = await generateStyledQRCode({
      data: url_qr_code,
      primaryColor,
      logo: '/logoguax.svg',
    });
  }

  return {
    ...data,
    qr_code_img,
  };
}

export default function VerificationOrderDetail({
  operationId,
  data,
}: {
  operationId: number;
  data: any;
}) {
  const { converRawDateToDateTimeFormat } = useConvertDate();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const activePayment = useActivePayment();
  const [theme] = useTheme();
  const methods = useForm();
  const {
    control,
    handleSubmit,
    watch,
    formState: { isSubmitting },
  } = methods;

  const [showAction, setShowAction] = useState({
    cancel_order: false,
    verify: false,
    print_waybill: false,
  });
  const [showPreviewWaybill, setShowPreviewWaybill] = useState({
    show: false,
    data: [],
    template: '',
  });
  const [currentPage, setCurrentPage] = useState(0);
  const { getOptionsByModel } = useCommonAPI();
  const { currencySymbol } = formatCurrency();
  const { formatNumber } = useFormatNumber();
  const { format: formatCurrencyPlacement } = useFormatCurrencyPlacement();
  const totalAmount = formatCurrencyPlacement(
    formatNumber(data?.financial_summary?.total_amount?.value),
    currencySymbol
  );
  // Thêm state để lưu print data
  const [printData, setPrintData] = useState({
    data: null,
    template: '',
    show: false,
  });

  // Tạo ref cho print component
  const printAllPagesRef = useRef<HTMLDivElement>(null);

  // Setup react-to-print cho tất cả trang
  const reactToPrintAllPages = useReactToPrint({
    contentRef: printAllPagesRef,
    pageStyle: `
      @media print {
        body, * {
          background: white !important;
          color: black !important;
        }
      }
    `,
  });

  if (!data?.id) return null;

  const setHideModal = () => {
    setShowAction({ cancel_order: false, verify: false, print_waybill: false });
  };

  const handleVerifyOrder = async () => {
    setLoading(true);
    const formData = { operation_ids: [operationId] };
    const { success, message } = await API.post(endpoint.verifyOders, formData);
    if (success) {
      setShowAction({
        cancel_order: false,
        verify: false,
        print_waybill: false,
      });
      navigate(-1);
      ToastTopHelper.success(message || t('Verified Success'));
    }
    setLoading(false);
  };
  const [loading, setLoading] = useState<boolean>(false);

  const handleCancelOrder = async (reason: string) => {
    setLoading(true);
    const formData = { reason_note: reason, is_system: false };
    const { success, message } = await API.post(
      endpoint.cancelOperationOrder(operationId),
      formData,
    );
    if (success) {
      setShowAction({
        cancel_order: false,
        verify: false,
        print_waybill: false,
      });
      navigate(-1);
      ToastTopHelper.success(message || t('Cancel Order Success'));
    }
    setLoading(false);
  };

  const handlePrintWaybill = async () => {
    setLoading(true);
    const waybillTemplate = watch('waybill_template');

    if (!waybillTemplate?.value) {
      ToastTopHelper.error(t('Please select a waybill template'));
      return;
    }

    try {
      // Get preview data
      const { success, data: previewData } = await API.get(
        endpoint.previewWaybill(data?.id, waybillTemplate.value),
      );

      if (!success) {
        ToastTopHelper.error(t('Failed to load waybill data'));
        return;
      }
      const { success: successPrint, data: printData } = await API.get(
        endpoint.printWaybill(operationId, waybillTemplate.value),
      );

      if (!successPrint) {
        ToastTopHelper.error(t('Failed to load waybill data'));
        return;
      }

      // Prepare data for all pages
      const items = previewData.data.items || [];
      const qrCodes = previewData.data.qr_code || [];
      const commonData = { ...previewData.data };
      delete commonData.items;
      delete commonData.qr_code;

      const pagesData = items.map((item, idx) => ({
        ...commonData,
        qr_code: qrCodes[idx],
        items: [item],
      }));

      const pagesDataWithQR = await Promise.all(
        pagesData.map(async (pageData) => await addQRCodeToData(pageData)),
      );

      setPrintData({
        data: pagesDataWithQR,
        template: previewData?.html,
        show: true,
      });

      // Close template selection modal
      setShowAction({
        cancel_order: false,
        verify: false,
        print_waybill: false,
      });

      // Wait for component to render then print
      setTimeout(() => {
        reactToPrintAllPages();

        setTimeout(() => {
          setPrintData({
            data: null,
            template: '',
            show: false,
          });

          methods.setValue('waybill_template', null);
          navigate(-1);
        }, 1000);
      }, 500);
    } catch (error) {
      console.error('Print error:', error);
      ToastTopHelper.error(t('Print failed'));
    }
    setLoading(false);
  };

  const onSubmit = (formData: any) => {
    if (showAction.cancel_order && formData.reason) {
      handleCancelOrder(formData.reason);
    } else if (showAction.verify) {
      handleVerifyOrder();
    } else if (showAction.print_waybill) {
      handlePrintWaybill();
    }
  };

  const handlePreviewWaybill = async () => {
    const waybillTemplate = watch('waybill_template');

    const { success, data: previewData } = await API.get(
      endpoint.previewWaybill(data?.id, waybillTemplate.value),
    );
    if (success) {
      const items = previewData.data.items || [];
      const qrCodes = previewData.data.qr_code || [];
      const commonData = { ...previewData.data };
      delete commonData.items;
      delete commonData.qr_code;

      const pagesData = items.map((item, idx) => ({
        ...commonData,
        qr_code: qrCodes[idx],
        items: [item],
      }));

      const pagesDataWithQR = await Promise.all(
        pagesData.map(async (pageData) => await addQRCodeToData(pageData)),
      );

      console.log('pagesDataWithQR', pagesDataWithQR);

      setCurrentPage(0);
      setShowPreviewWaybill({
        show: true,
        data: pagesDataWithQR,
        template: previewData?.html,
      });
    }
  };

  const packageData = data?.items?.map((item: any) => ({
    id: item.id,
    price: item.amount,
    list_item: [
      {
        name: t('Package ID'),
        value: item.code,
      },
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

  return (
    <FormProvider {...methods}>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CustomBreadcrumb
          items={[{ url: '/delivery-operation' }, { text: t('Order Detail') }]}
          buttons={
            data?.mapped_status_code === 'verified_order'
              ? [
                <CustomBtn
                  key="print"
                  label={t('Print Waybill')}
                  type="button"
                  variant="contained"
                  color="primary"
                  size="md"
                  onClick={() => {
                    setShowAction((prevAction) => ({
                      ...prevAction,
                      print_waybill: true,
                    }));
                  }}
                />,
              ]
              : [
                <CustomBtn
                  key="print"
                  label={t('Cancel Order')}
                  variant="outline"
                  type="button"
                  color="secondary"
                  size="md"
                  onClick={() =>
                    setShowAction((prevAction) => ({
                      ...prevAction,
                      cancel_order: true,
                    }))
                  }
                />,
                <CustomBtn
                  key="print"
                  label={t('Verify')}
                  type="submit"
                  variant="contained"
                  color="primary"
                  size="md"
                  loading={loading || isSubmitting}
                  disabled={loading || isSubmitting}
                  onClick={() =>
                    setShowAction((prevAction) => ({
                      ...prevAction,
                      verify: true,
                    }))
                  }
                />,
              ]
          }
        />
        <Main>
          <Box
            sx={{
              display: 'grid',
              gap: '1rem',
              gridTemplateColumns: '8fr 4fr',
              alignItems: 'start',
            }}
          >
            <div
              className="d-flex flex-column"
              style={{ gap: '1rem' }}
            >
              {/* Order Info Card */}
              <FormBlock>
                <div
                  style={{
                    display: 'flex',
                    marginBottom: '0.5rem',
                  }}
                >
                  <div style={{ display: 'flex', flex: 1 }}>
                    <div
                      style={{
                        color: textLabel[theme],
                        fontSize: '0.875rem',
                        marginBottom: 4,
                        flex: 1,
                      }}
                    >
                      {t('Order ID')}
                    </div>
                    <div
                      style={{
                        color: textValue[theme],
                        fontSize: '0.875rem',
                        flex: 1,
                      }}
                    >
                      {data?.order_code || '-'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flex: 1 }}>
                    <div
                      style={{
                        flex: 1,
                        color: textLabel[theme],
                        fontSize: '0.875rem',
                        marginBottom: 4,
                      }}
                    >
                      {t('Status')}
                    </div>
                    {data?.mapped_status_code ? (
                      <div
                        style={{
                          display: 'grid',
                          gap: '1rem',
                          gridTemplateColumns: '1fr 1fr',
                        }}
                      >
                        {data?.mapped_status_list?.length > 0
                          ? data?.mapped_status_list?.map(
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
                                status_code: item.code,
                                backgroundColor: item.background_color,
                                color: item.text_color,
                                border: item.border_color,
                                isShowButton: false,
                              }),
                          )
                          : data.mapped_status_code &&
                          formatStatusDeliveryInquiry({
                            t,
                            status_name: data?.mapped_status?.name,
                            status_code: data?.mapped_status_code,
                            backgroundColor:
                              data?.mapped_status_background_color,
                            color: getContrastTextColor(
                              data?.mapped_status_background_color,
                            ),
                            border: data?.mapped_status_border_color,
                            isShowButton: false,
                          })}
                      </div>
                    ) : (
                      <div style={{ flex: 1 }}>
                        <span
                          style={{
                            padding: '0.25rem 0.5rem',
                            lineHeight: 1.2,
                            fontSize: '0.875rem',
                          }}
                        >
                          -
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <div style={{ display: 'flex', flex: 1 }}>
                    <div
                      style={{
                        flex: 1,
                        color: textLabel[theme],
                        fontSize: '0.875rem',
                        marginBottom: 4,
                      }}
                    >
                      {t('Order Time')}
                    </div>
                    <div
                      style={{
                        flex: 1,
                        color: textValue[theme],
                        fontSize: '0.875rem',
                      }}
                    >
                      {converRawDateToDateTimeFormat(data.created_on)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flex: 1 }}>
                    <div
                      style={{
                        flex: 1,
                        color: textLabel[theme],
                        fontSize: '0.875rem',
                        marginBottom: 4,
                      }}
                    >
                      {t('Payment Time')}
                    </div>
                    <div
                      style={{
                        flex: 1,
                        color: textValue[theme],
                        fontSize: '0.875rem',
                      }}
                    >
                      {converRawDateToDateTimeFormat(data?.paid_time) || '-'}
                    </div>
                  </div>
                </div>
                {data.verified_time && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginTop: 8,
                    }}
                  >
                    <div
                      style={{
                        flex: 1,
                        color: textLabel[theme],
                        fontSize: '0.875rem',
                      }}
                    >
                      {t('Order Verification Time')}
                    </div>
                    <div
                      style={{
                        flex: 1,
                        color: textValue[theme],
                        fontSize: '0.875rem',
                      }}
                    >
                      {converRawDateToDateTimeFormat(data?.verified_time) || '-'}
                    </div>
                    <div style={{ flex: 2 }} />
                  </div>
                )}
              </FormBlock>

              {/* Sender */}
              <FormBlock>
                <div
                  style={{
                    fontWeight: 600,
                    fontSize: '1.125rem',
                    marginBottom: '0.75rem',
                    color: textValue[theme],
                  }}
                >
                  {t('Sender')}
                </div>
                <div
                  style={{
                    background: infoBg[theme],
                    borderRadius: 12,
                    padding: '0.75rem',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '0 0 8px',
                      borderBottom: `1px solid ${border[theme]}`,
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>{t('Name')}</span>
                    <span>{data?.sender_name || '-'}</span>
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '8px 0',
                      borderBottom: `1px solid ${border[theme]}`,
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>
                      {t('Phone Number')}
                    </span>
                    <span>{data?.sender_phone || '-'}</span>
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: data?.sender_note ? '8px 0' : '8px 0 0',
                      borderBottom: data?.sender_note
                        ? `1px solid ${border[theme]}`
                        : 'none',
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>
                      {t('Pickup Location')}
                    </span>
                    <span>{data?.origin || '-'}</span>
                  </div>
                  {data?.sender_note && (
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '8px 0 0',
                        borderBottom: 'none',
                        color: textValue[theme],
                      }}
                    >
                      <span style={{ color: textLabel[theme] }}>
                        {t('Note')}
                      </span>
                      <span>{data?.sender_note || '-'}</span>
                    </div>
                  )}
                </div>
                {/* Recipient */}
                <div
                  style={{
                    fontWeight: 600,
                    fontSize: '1.125rem',
                    margin: '0.75rem 0',
                    color: textValue[theme],
                  }}
                >
                  {t('Recipient')}
                </div>
                <div
                  style={{
                    background: infoBg[theme],
                    borderRadius: 12,
                    padding: '0.75rem',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '0 0 8px',
                      borderBottom: `1px solid ${border[theme]}`,
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>{t('Name')}</span>
                    <span>{data?.recipient_name || '-'}</span>
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '8px 0',
                      borderBottom: `1px solid ${border[theme]}`,
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>
                      {t('Phone Number')}
                    </span>
                    <span>{data?.recipient_phone || '-'}</span>
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: data?.recipient_note ? '8px 0' : '8px 0 0',
                      borderBottom: data?.recipient_note
                        ? `1px solid ${border[theme]}`
                        : 'none',
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>
                      {t('Address')}
                    </span>
                    <span>{data?.recipient_address || '-'}</span>
                  </div>
                  {data?.recipient_note && (
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        padding: '8px 0 0',
                        borderBottom: 'none',
                        color: textValue[theme],
                      }}
                    >
                      <span style={{ color: textLabel[theme] }}>
                        {t('Note')}
                      </span>
                      <span>{data?.recipient_note || '-'}</span>
                    </div>
                  )}
                </div>

                {/* Delivery Option */}
                <div
                  style={{
                    fontWeight: 600,
                    fontSize: '1.125rem',
                    margin: '0.75rem 0',
                    color: textValue[theme],
                  }}
                >
                  {t('Delivery Option')}
                </div>
                <div
                  style={{
                    background: infoBg[theme],
                    borderRadius: 12,
                    padding: '0.75rem',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      borderBottom: 'none',
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>
                      {t('Location')}
                    </span>
                    <span>{data?.destination || '-'}</span>
                  </div>
                </div>
              </FormBlock>
            </div>

            <FormBlock>
              <Box sx={{ height: 'fit-content' }}>
                <div className="header-title pb-3">{t('Invoice')}</div>
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
                              theme === 'dark' ? Colors.Gray7 : '#F6F7F8',
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
                          !activePayment && packageData.length - 1 === index
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
                        {totalAmount ||
                          '-'}
                      </span>
                    </div>
                    <div className="d-flex justify-content-between header-title pb-0">
                      <span>{t('Payment Method')}</span>
                      <span>
                        {t(data?.payment_details?.payment_method || '-')}
                      </span>
                    </div>
                  </div>
                )}
              </Box>
            </FormBlock>
          </Box>
        </Main>
        <CustomModal
          title={t('Cancel Order')}
          show={showAction.cancel_order}
          onHide={() =>
            setShowAction((prevAction) => ({
              ...prevAction,
              cancel_order: false,
            }))
          }
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
              placeholder={t('Reason')}
            />
          </div>
          <ActionBtn
            styles={{ maxWidth: '100%' }}
            leftButtons={[
              <CustomBtn
                type="submit"
                variant="contained"
                color="primary"
                size="lg"
                onClick={() => {
                  handleSubmit(onSubmit)();
                }}
                label={t('Confirm')}
                disabled={!watch('reason') || loading}
                loading={loading}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={() =>
                  setShowAction((prevAction) => ({
                    ...prevAction,
                    cancel_order: false,
                  }))
                }
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>
        <CustomModal
          title={t('Select Waybill Template')}
          show={showAction.print_waybill}
          onHide={() => {
            setShowAction((prevAction) => ({
              ...prevAction,
              print_waybill: false,
            }));
            methods.setValue('waybill_template', null);
          }}
        >
          <div
            style={{
              width: '45rem',
              display: 'flex',
              padding: '0.5rem 0',
              gap: '1.5rem',
              alignItems: 'center',
            }}
          >
            <PaginationSelect
              name="waybill_template"
              label=""
              control={control}
              placeholder={t('Select')}
              loadOptions={getOptionsByModel({
                name_modal: 'printformat',
              })}
              className="flex-fill"
            />
            <Box
              className="special-label cursor-pointer"
              sx={{
                '&:hover': {
                  color: 'var(--ga-primary)',
                },
              }}
              onClick={handlePreviewWaybill}
            >
              <BsEye size={18} />
            </Box>
          </div>
          <Typography
            variant="body1"
            sx={{
              color: Colors.Gray5,
              mt: '0.125rem',
            }}
          >
            {t(
              'Please select a terminal to transfer and store the returned order.',
            )}
          </Typography>
          <ActionBtn
            styles={{ maxWidth: '100%' }}
            leftButtons={[
              <CustomBtn
                type="submit"
                variant="contained"
                color="primary"
                size="lg"
                onClick={handleSubmit(onSubmit)}
                loading={loading || isSubmitting}
                label={t('Print')}
                disabled={!watch('waybill_template') || loading || isSubmitting}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={() => {
                  setShowAction((prevAction) => ({
                    ...prevAction,
                    print_waybill: false,
                  }));
                  methods.setValue('waybill_template', null);
                }}
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>
        <CustomModal
          title={t('Preview')}
          show={
            showPreviewWaybill.show &&
            showPreviewWaybill.data &&
            showPreviewWaybill.template
          }
          onHide={() => {
            setShowPreviewWaybill({ show: false, data: '', template: '' });
            setCurrentPage(0);
          }}
          id="preview-modal"
        >
          {Array.isArray(showPreviewWaybill.data) &&
            showPreviewWaybill.data.length > 1 && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: 16,
                  margin: '1rem 0',
                }}
              >
                <CustomBtn
                  type="button"
                  onClick={() =>
                    setCurrentPage((prev) => Math.max(prev - 1, 0))
                  }
                  disabled={currentPage === 0}
                  style={{ padding: '0.675rem 1rem' }}
                  variant="outline"
                  color="secondary"
                  size="md"
                  label={'←'}
                />
                <span style={{ fontSize: '1rem', fontWeight: 400 }}>
                  {currentPage + 1} / {showPreviewWaybill.data.length}
                </span>
                <CustomBtn
                  type="button"
                  variant="outline"
                  color="secondary"
                  size="md"
                  onClick={() =>
                    setCurrentPage((prev) =>
                      Math.min(prev + 1, showPreviewWaybill.data.length - 1),
                    )
                  }
                  disabled={currentPage === showPreviewWaybill.data.length - 1}
                  style={{ padding: '0.675rem 1rem' }}
                  label={'→'}
                />
              </div>
            )}
          <div
            style={{
              height: '40.5rem',
              width: '60rem',
              overflow: 'auto',
              marginBottom: '1rem',
            }}
          >
            {Array.isArray(showPreviewWaybill.data) ? (
              <div>
                <NunjucksRenderer
                  template={replaceQRParagraphWithDiv(
                    showPreviewWaybill.template,
                  )}
                  data={showPreviewWaybill.data[currentPage]}
                  className="tiptap-preview-content"
                />
              </div>
            ) : (
              <NunjucksRenderer
                template={replaceQRParagraphWithDiv(
                  showPreviewWaybill.template,
                )}
                data={showPreviewWaybill.data}
                className="tiptap-preview-content"
              />
            )}
          </div>
          <CenterBtn
            color="secondary"
            type="button"
            variant="outline"
            size="lg"
            onClick={() => {
              setShowPreviewWaybill({ show: false, data: '', template: '' });
              setCurrentPage(0);
            }}
            label={t('Close')}
          />
        </CustomModal>
        {printData.show && printData.data && printData.template && (
          <div
            ref={printAllPagesRef}
            style={{
              position: 'absolute',
              // left: "-9999px",
              top: '0px',
              width: '210mm',
              // visibility: "hidden",
              background: theme === 'dark' ? '#212529' : '#fff',
            }}
          >
            {Array.isArray(printData.data) ? (
              printData.data.map((pageData, index) => (
                <div
                  key={index}
                  style={{
                    pageBreakAfter:
                      index < printData.data.length - 1 ? 'always' : 'auto',
                    minHeight: '297mm',
                    padding: '15mm',
                    boxSizing: 'border-box',
                  }}
                >
                  <NunjucksRenderer
                    template={replaceQRParagraphWithDiv(printData.template)}
                    data={pageData}
                    className="tiptap-preview-content"
                  />
                </div>
              ))
            ) : (
              <div>
                <NunjucksRenderer
                  template={replaceQRParagraphWithDiv(printData.template)}
                  data={printData.data}
                  className="tiptap-preview-content"
                />
              </div>
            )}
          </div>
        )}
      </form>
    </FormProvider>
  );
}
