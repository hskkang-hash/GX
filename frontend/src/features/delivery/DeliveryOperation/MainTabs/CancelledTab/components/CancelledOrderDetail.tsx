import { Box } from '@mui/material';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  CustomBreadcrumb,
  FormBlock,
  Main,
  useTheme,
  useActivePayment,
} from 'rj-core';

import ExpanDropDown from '@/components/Form/ExpanDropDown';
import Colors, { border, infoBg, textLabel, textValue } from '@/configs/Colors';

import { getContrastTextColor } from '../../../../../../utils/utils';
import { formatStatusDeliveryInquiry } from '../../../../deliveryInquiry/utils/StatusColorInquiry';
import { useFormatNumber } from '@/utils/formatConfig';
import { formatCurrency, useFormatCurrencyPlacement } from '@/utils/formatCurrency';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

export default function CancelledOrderDetail({
  operationId,
  data,
}: {
  operationId: number;
  data: any;
}) {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const methods = useForm();
  const activePayment = useActivePayment();
  const { currencySymbol } = formatCurrency();
  const { formatNumber } = useFormatNumber();
  const { converRawDateToDateTimeFormat } = useConvertDate();
  const { format: formatCurrencyPlacement } = useFormatCurrencyPlacement();
  const totalAmount = formatCurrencyPlacement(
    formatNumber(data?.financial_summary?.total_amount?.value),
    currencySymbol
  );
  if (!data?.id) return null;

  return (
    <FormProvider {...methods}>
      <form>
        <CustomBreadcrumb
          items={[{ url: '/delivery-operation' }, { text: t('Order Detail') }]}
          buttons={[]}
        />
        <Main>
          <div className="grid-column-2 mb-3">
            <FormBlock
              style={{
                backgroundColor: theme === 'dark' ? '#513D2B' : '#FBEBDD',
                color: theme === 'dark' ? '#ECECEF' : Colors.Gray7,
                padding: '8px 12px',
              }}
            >
              <b>{t('Reason')}:</b> {data?.cancel_reason}
            </FormBlock>
          </div>
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
                    {t('Order Cancellation Time')}
                  </div>
                  <div
                    style={{
                      flex: 1,
                      color: textValue[theme],
                      fontSize: '0.875rem',
                    }}
                  >
                    {data?.cancel_time ? converRawDateToDateTimeFormat(data?.cancel_time) : '-'}
                  </div>
                  <div
                    style={{
                      flex: 1,
                      color: textLabel[theme],
                      fontSize: '0.875rem',
                    }}
                  >
                    {t('Refund Time')}
                  </div>
                  <div
                    style={{
                      flex: 1,
                      color: textValue[theme],
                      fontSize: '0.875rem',
                    }}
                  >
                    {data?.refunded_time ? converRawDateToDateTimeFormat(data?.refunded_time) : '-'}
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
                    {t('Cancelled By')}
                  </div>
                  <div
                    style={{
                      flex: 1,
                      color: textValue[theme],
                      fontSize: '0.875rem',
                    }}
                  >
                    {data?.cancelled_by__name || t('Automated cancellation')}
                  </div>
                  <div style={{ flex: 2 }} />
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
                      padding: data?.sender_note ? '8px 0' : '8px 00',
                      borderBottom: data?.sender_note
                        ? `1px solid ${border[theme]}`
                        : 'none',
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>
                      {t('Pickup Location')}
                    </span>
                    <span>{data?.pickup_location || '-'}</span>
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

            {/* Invoice */}
            <div
              className="d-flex flex-column"
              style={{ gap: '1rem' }}
            >
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
                        marginBottom: 8,
                        fontSize: '1.125rem',
                        color: textValue[theme],
                      }}
                    >
                      <span>
                        {t('Package')} {idx + 1}
                      </span>{' '}
                      {pkg?.amount ? (
                        <span>{formatCurrencyPlacement(
                          formatNumber(pkg?.amount),
                          currencySymbol
                        )}  </span>
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
                        fontWeight: 600,
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
            </div>
          </Box>
        </Main>
      </form>
    </FormProvider>
  );
}
