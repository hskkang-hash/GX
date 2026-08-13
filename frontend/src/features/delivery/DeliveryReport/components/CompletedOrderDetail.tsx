import Timeline from '@mui/lab/Timeline';
import TimelineSeparator from '@mui/lab/TimelineSeparator';
import { Box } from '@mui/material';
import { useEffect, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  CustomBreadcrumb,
  CustomBtn,
  CustomModal,
  FormBlock,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useActivePayment,
  useTheme,
} from 'rj-core';

import ExpanDropDown from '@/components/Form/ExpanDropDown';
import { Map } from '@/components/maps';
import Colors, { border, infoBg, textLabel, textValue } from '@/configs/Colors';
import {
  CustomTimelineConnector,
  CustomTimelineContent,
  CustomTimelineDot,
  CustomTimelineItem,
} from '@/features/delivery/deliveryInquiry/detailOrder/style';
import { formatStatusDeliveryInquiry } from '@/features/delivery/deliveryInquiry/utils/StatusColorInquiry';
import API, { endpoint } from '@/services/API';
import { getContrastTextColor } from '@/utils/utils';
import { useFormatNumber } from '@/utils/formatConfig';
import { formatCurrency, useFormatCurrencyPlacement } from '@/utils/formatCurrency';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

export default function CompletedOrderDetail({
  operationId,
  data,
}: {
  operationId: number;
  data: any;
}) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [theme] = useTheme();
  const methods = useForm();
  const { control, handleSubmit, formState, watch } = methods;
  const [showAction, setShowAction] = useState({
    complete: false,
  });
  const activePayment = useActivePayment();
  const [routeMap, setRouteMap] = useState([]);
  const [mapBounds, setMapBounds] = useState<{
    sw: { lat: number; lng: number };
    ne: { lat: number; lng: number };
  } | null>(null);
  const [mapCenter, setMapCenter] = useState<{
    lat: number;
    lng: number;
  } | null>(null);
  const { currencySymbol } = formatCurrency();
  const { formatNumber } = useFormatNumber();
  const { format: formatCurrencyPlacement } = useFormatCurrencyPlacement();
  const { converRawDateToDateTimeFormat } = useConvertDate();
  const totalAmount = formatCurrencyPlacement(
    formatNumber(data?.financial_summary?.total_amount?.value),
    currencySymbol
  );
  useEffect(() => {
    const fetchRouteDetail = async () => {
      setRouteMap([]);
      const { success: routeDetailSuccess, data: routeDetailData } =
        await API.get(endpoint.routes + `/${data?.route}`);

      if (routeDetailSuccess && routeDetailData) {

        const routesMapData =
          routeDetailData?.route_terminals?.map(
            (item: {
              latitude: number;
              longitude: number;
              name: string;
              for_robot: boolean;
            }) => {
              return {
                lat: item.latitude,
                lng: item.longitude,
                name: item.name,
                for_robot: item.for_robot,
              };
            },
          ) || [];
        setRouteMap(routesMapData);
      }
    };

    if (data?.route) {
      fetchRouteDetail();
    }
  }, [data]);

  useEffect(() => {
    if (routeMap.length > 0) {
      // Calculate bounds
      const lats = routeMap.map((p) => p.lat);
      const lngs = routeMap.map((p) => p.lng);
      console.log('lats', lats);
      console.log('lngs', lngs);

      const bounds = {
        sw: {
          lat: Math.min(...lats), // Add some padding
          lng: Math.min(...lngs),
        },
        ne: {
          lat: Math.max(...lats),
          lng: Math.max(...lngs),
        },
      };
      setMapBounds(bounds);

      // Calculate center
      const center = {
        lat: (bounds.sw.lat + bounds.ne.lat) / 2,
        lng: (bounds.sw.lng + bounds.ne.lng) / 2,
      };
      setMapCenter(center);
    }
  }, [routeMap]);

  if (!data?.id) return null;

  const handleCompleteOrder = async () => {
    const formData = { operation_ids: [operationId] };
    const { success, message } = await API.post(
      endpoint.actionCompletedOrder,
      formData,
    );

    if (success) {
      setShowAction({
        complete: false,
      });
      navigate(-1);
      ToastTopHelper.success(message || t('Completed Success'));
    }
  };

  const onSubmit = (formData: any) => {
    if (showAction.complete) {
      handleCompleteOrder();
    }
  };
  const [loading, setLoading] = useState(false);

  const handleDownloadReport = async (id: number) => {
    try {
      setLoading(true);
      const response = await API.get(endpoint.downloadReport(id));

      if (response.success && response.data?.file_url) {
        const fileUrl = response.data.file_url;
        const fileName = response.data.file_name || `report-${id}.pdf`;

        const fileResponse = await fetch(fileUrl);
        const blob = await fileResponse.blob();

        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        window.URL.revokeObjectURL(url);

        ToastTopHelper.success(t('Report downloaded successfully'));
      } else {
        ToastTopHelper.error(response.data.message);
      }
    } catch (error) {
      setLoading(false);
      ToastTopHelper.error(t('Failed to download report'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <FormProvider {...methods}>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CustomBreadcrumb
          items={[{ url: '/delivery-report' }, { text: t('Order Detail') }]}
          buttons={[
            <CustomBtn
              key="download-report"
              label={t('Download Report')}
              type="button"
              variant="outline"
              color="primary"
              size="md"
              loading={loading}
              actionType={ROLE_PERMISSION.READ}
              onClick={() => handleDownloadReport(operationId)}
            />,
          ]}
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
                          : data?.mapped_status_code &&
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
                      {data.created_on ? converRawDateToDateTimeFormat(data.created_on) : '-'}
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
                      {data?.paid_time ? converRawDateToDateTimeFormat(data?.paid_time) : '-'}
                    </div>
                  </div>
                </div>
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
                    {data?.verified_time ? converRawDateToDateTimeFormat(data?.verified_time) : '-'}
                  </div>
                  <div
                    style={{
                      flex: 1,
                      color: textLabel[theme],
                      fontSize: '0.875rem',
                    }}
                  >
                    {t('Arrival Time')}
                  </div>
                  <div
                    style={{
                      flex: 1,
                      color: textValue[theme],
                      fontSize: '0.875rem',
                    }}
                  >
                    {data?.arrived_time ? converRawDateToDateTimeFormat(data?.arrived_time) : '-'}
                  </div>
                </div>
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
                    {t('Order Completion Time')}
                  </div>
                  <div
                    style={{
                      flex: 1,
                      color: textValue[theme],
                      fontSize: '0.875rem',
                    }}
                  >
                    {data?.completed_time ? converRawDateToDateTimeFormat(data?.completed_time) : '-'}
                  </div>
                  <div
                    style={{
                      flex: 2,
                      color: textLabel[theme],
                      fontSize: '0.875rem',
                    }}
                  ></div>
                </div>
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
                      padding: '8px 0',
                      borderBottom: `1px solid ${border[theme]}`,
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>
                      {t('Pickup Location')}
                    </span>
                    <span>{data?.pickup_location || '-'}</span>
                  </div>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '8px 0',
                      borderBottom: 'none',
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>{t('Note')}</span>
                    <span>{data?.sender_note || '-'}</span>
                  </div>
                </div>

                {/* Package */}
                <ExpanDropDown
                  label={t('History')}
                  defaultExpanded={false}
                  lableSize="1.125rem"
                  // noSpace={true}
                  sx={{
                    margin: '0.75rem 0 !important',
                    '.MuiAccordionDetails-root': {
                      padding: '0px !important',
                    },
                    '& .MuiButtonBase-root.MuiAccordionSummary-root': {
                      padding: '0 !important',
                    },
                    '& .MuiAccordionSummary-content': {
                      margin: '0 !important',
                    },
                  }}
                >
                  {data?.items?.map((pkg: any, idx: number) => (
                    <Box
                      key={idx}
                      sx={{ marginBottom: '0.5rem' }}
                    >
                      <div
                        className="d-flex justify-content-between"
                        style={{
                          fontWeight: 500,
                          marginBottom: '0.5rem',
                          fontSize: '1.125rem',
                          color: textValue[theme],
                        }}
                      >
                        <span>
                          {t('Package')} {idx + 1}
                        </span>
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
                            padding: '0 0 4px',
                            borderBottom: `1px solid ${border[theme]}`,
                            color: textValue[theme],
                          }}
                        >
                          <span style={{ color: textLabel[theme] }}>
                            {t('Package ID')}
                          </span>
                          <span>{pkg?.code || '-'}</span>
                        </div>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: '4px 0',
                            borderBottom: `1px solid ${border[theme]}`,
                            color: textValue[theme],
                          }}
                        >
                          <span style={{ color: textLabel[theme] }}>
                            {t('Weight')}
                          </span>
                          {pkg?.weight && pkg?.weight?.value ? (
                            <span>
                              {pkg?.weight?.value} {pkg?.weight?.unit}
                            </span>
                          ) : (
                            <span>-</span>
                          )}
                        </div>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: '4px 0',
                            borderBottom: `1px solid ${border[theme]}`,
                            color: textValue[theme],
                          }}
                        >
                          <span style={{ color: textLabel[theme] }}>
                            {t('Dimension')}
                          </span>
                          {pkg?.dimension_l &&
                            pkg?.dimension_w &&
                            pkg?.dimension_h ? (
                            <span>
                              {pkg?.dimension_l?.value}
                              {pkg?.dimension_l?.unit} x{' '}
                              {pkg?.dimension_w?.value}
                              {pkg?.dimension_w?.unit} x{' '}
                              {pkg?.dimension_h?.value}
                              {pkg?.dimension_h?.unit}
                            </span>
                          ) : (
                            <span>-</span>
                          )}
                        </div>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: '4px 0',
                            borderBottom: `1px solid ${border[theme]}`,
                            color: textValue[theme],
                          }}
                        >
                          <span style={{ color: textLabel[theme] }}>
                            {t('Item Type')}
                          </span>
                          <span>{pkg?.item_type__name || '-'}</span>
                        </div>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: '4px 0',
                            borderBottom: `1px solid ${border[theme]}`,
                            color: textValue[theme],
                          }}
                        >
                          <span style={{ color: textLabel[theme] }}>
                            {t('Waterproof')}
                          </span>
                          <span>{pkg?.is_waterproof ? t('Yes') : t('No')}</span>
                        </div>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            padding: pkg?.note ? '4px 0' : '4px 0 0',
                            borderBottom: pkg?.note
                              ? `1px solid ${border[theme]}`
                              : 'none',
                            color: textValue[theme],
                          }}
                        >
                          <span style={{ color: textLabel[theme] }}>
                            {t('Packaging Type')}
                          </span>
                          <span>{pkg?.package_id__name || '-'}</span>
                        </div>
                        {pkg?.note && (
                          <div
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              padding: '4px 0',
                              color: textValue[theme],
                            }}
                          >
                            <span style={{ color: textLabel[theme] }}>
                              {t('Note')}
                            </span>
                            <span>{pkg?.note || '-'}</span>
                          </div>
                        )}
                      </div>
                    </Box>
                  ))}
                </ExpanDropDown>

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
                      padding: '8px 0',
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
                        padding: '8px 0',
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
                      padding: '8px 0',
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

              <Box
                flex={1}
                sx={{ position: 'relative' }}
              >
                <Map
                  center={mapCenter}
                  operatingMarkers={routeMap.length > 0 ? routeMap : []}
                  polylines={routeMap.length > 0 ? [routeMap] : []}
                  bounds={mapBounds}
                  style={{ height: 350 }}
                />
              </Box>
            </div>

            <div
              className="d-flex flex-column"
              style={{ gap: '1rem' }}
            >
              {/* Invoice */}
              <FormBlock>
                <div
                  style={{
                    fontWeight: 600,
                    fontSize: '1.125rem',
                    marginBottom: '1rem',
                    color: textValue[theme],
                  }}
                >
                  {t('Invoice')}
                </div>
                {data?.items?.map((pkg: any, idx: number) => (
                  <div
                    key={idx}
                    style={{ marginBottom: '1rem' }}
                  >
                    <div
                      className="d-flex justify-content-between"
                      style={{
                        marginBottom: '0.5rem',
                        fontSize: '1.125rem',
                        color: textValue[theme],
                      }}
                    >
                      <span>
                        {t('Package')} {idx + 1}
                      </span>
                      {pkg?.amount ? (
                        <span>{formatCurrencyPlacement(formatNumber(pkg?.amount), currencySymbol)}</span>
                      ) : (
                        <span>-</span>
                      )}
                    </div>
                  </div>
                ))}
                {activePayment && (
                  <>
                    <div
                      style={{
                        height: 1,
                        width: '100%',
                        background: border[theme],
                      }}
                    />
                    <div
                      className="d-flex justify-content-between"
                      style={{
                        fontWeight: 700,
                        fontSize: '1.125rem',
                        marginTop: '1rem',
                        color: textValue[theme],
                      }}
                    >
                      <span>{t('Total')}</span>
                      <span>
                        {totalAmount ||
                          '-'}
                      </span>
                    </div>
                    <div
                      className="d-flex justify-content-between"
                      style={{
                        fontWeight: 600,
                        fontSize: '1.125rem',
                        marginTop: '0.75rem',
                        color: textValue[theme],
                      }}
                    >
                      <span>{t('Payment Method')}</span>
                      <span>
                        {t(data?.payment_details?.payment_method) || '-'}
                      </span>
                    </div>
                  </>
                )}
              </FormBlock>
              <ExpanDropDown
                label={t('History')}
                // defaultExpanded={false}
                lableSize="1.125rem"
              >
                <Timeline sx={{ padding: '10px 5px 2px' }}>
                  {data?.history.map((item: any, index: number) => (
                    <CustomTimelineItem>
                      <TimelineSeparator>
                        <CustomTimelineDot />
                        <CustomTimelineConnector />
                      </TimelineSeparator>
                      <CustomTimelineContent>
                        <span style={{ color: Colors.Gray5 }}>
                          {item?.created_on ? converRawDateToDateTimeFormat(item?.created_on) : '-'}
                        </span>
                        <span
                          style={{
                            color:
                              theme === 'dark'
                                ? Colors.Gray3
                                : Colors.PrimaryText,
                          }}
                        >
                          {item?.description}
                        </span>
                      </CustomTimelineContent>
                    </CustomTimelineItem>
                  ))}
                </Timeline>
              </ExpanDropDown>
            </div>
          </Box>
        </Main>
        <CustomModal
          title={t('Confirm Order Completion')}
          show={showAction.complete}
          onHide={() =>
            setShowAction((prevAction) => ({
              ...prevAction,
              complete: false,
            }))
          }
        >
          <div style={{ width: '30rem' }}>
            <div
              style={{
                fontSize: '14px',
                color: theme === 'dark' ? Colors.Gray4 : Colors.Gray6,
              }}
              className=""
            >
              {t('Are you sure you want to mark this order as completed?')}
            </div>
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
                loading={formState.isSubmitting}
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
                    complete: false,
                  }))
                }
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>
      </form>
    </FormProvider>
  );
}
