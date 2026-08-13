import { Box } from '@mui/material';
import { useTranslation } from 'react-i18next';
import {
  CenterBtn,
  CustomModal,
  FormBlock,
  useTheme,
  useActivePayment,
} from 'rj-core';

import ExpanDropDown from '@/components/Form/ExpanDropDown';
import { border, textLabel, textValue } from '@/configs/Colors';

import './OrderDetailModal.scss';
import { formatCurrency, useFormatCurrencyPlacement } from '@/utils/formatCurrency';
import { useFormatNumber } from '@/utils/formatConfig';

export default function OrderDetailModal({
  show,
  onHide,
  detailData,
}: {
  show: boolean;
  onHide: () => void;
  detailData: any;
}) {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const activePayment = useActivePayment();
  const { currencySymbol } = formatCurrency();
  const { formatNumber } = useFormatNumber();
  const { format: formatCurrencyPlacement } = useFormatCurrencyPlacement();
  const totalAmount = formatCurrencyPlacement(
    formatNumber(detailData?.financial_summary?.total_amount?.value),
    currencySymbol
  );
  console.log('detailData', detailData);
  return (
    <CustomModal
      id="order-detail-modal"
      title={t('Order Detail')}
      show={show}
      onHide={onHide}
    >
      {detailData && (
        <Box
          sx={{
            width: '100%',
            display: 'grid',
            gap: '1rem',
            gridTemplateColumns: '8fr 4fr',
            alignItems: 'start',
            pb: '20px',
          }}
        >
          <Box
            className="d-flex flex-column"
            sx={{
              background: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
              borderRadius: '8px',
            }}
          >
            {/* Sender */}
            <FormBlock
              style={{ background: 'transparent', padding: '0.75rem 1rem' }}
            >
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
                  background: theme === 'dark' ? '#1F1F20' : '#FFFFFF',
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
                  <span>{detailData?.sender_name || '-'}</span>
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
                  <span>{detailData?.sender_phone || '-'}</span>
                </div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: detailData?.sender_note ? '8px 0' : '8px 0 0',
                    borderBottom: detailData?.sender_note
                      ? `1px solid ${border[theme]}`
                      : 'none',
                    color: textValue[theme],
                  }}
                >
                  <span style={{ color: textLabel[theme] }}>
                    {t('Pickup Location')}
                  </span>
                  <span style={{ paddingLeft: '20px' }}>
                    {detailData?.origin || '-'}
                  </span>
                </div>
                {detailData?.sender_note && (
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '8px 0 0',
                      borderBottom: 'none',
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>{t('Note')}</span>
                    <span>{detailData?.sender_note || '-'}</span>
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
                  '&.MuiPaper-root.MuiAccordion-root': {
                    background: 'transparent !important',
                  },
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
                {detailData?.items?.map((pkg: any, idx: number) => (
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
                        background: theme === 'dark' ? '#1F1F20' : '#FFFFFF',
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
                            {pkg?.dimension_l?.unit} x {pkg?.dimension_w?.value}
                            {pkg?.dimension_w?.unit} x {pkg?.dimension_h?.value}
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
                  background: theme === 'dark' ? '#1F1F20' : '#FFFFFF',
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
                  <span>{detailData?.recipient_name || '-'}</span>
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
                  <span>{detailData?.recipient_phone || '-'}</span>
                </div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: detailData?.recipient_note ? '8px 0' : '8px 0 0',
                    borderBottom: detailData?.recipient_note
                      ? `1px solid ${border[theme]}`
                      : 'none',
                    color: textValue[theme],
                  }}
                >
                  <span style={{ color: textLabel[theme] }}>
                    {t('Address')}
                  </span>
                  <span>{detailData?.recipient_address || '-'}</span>
                </div>
                {detailData?.recipient_note && (
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '8px 0 0',
                      borderBottom: 'none',
                      color: textValue[theme],
                    }}
                  >
                    <span style={{ color: textLabel[theme] }}>{t('Note')}</span>
                    <span>{detailData?.recipient_note || '-'}</span>
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
                  background: theme === 'dark' ? '#1F1F20' : '#FFFFFF',
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
                  <span style={{ paddingLeft: '20px' }}>
                    {detailData?.destination || '-'}
                  </span>
                </div>
              </div>
            </FormBlock>
          </Box>

          {/* Invoice */}
          <Box
            className="d-flex flex-column"
            sx={{
              background: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
              borderRadius: '8px',
              gap: '1rem',
            }}
          >
            <FormBlock
              style={{ background: 'transparent', padding: '0.75rem 1rem' }}
            >
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
              {detailData?.items?.map((pkg: any, idx: number) => (
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
                    </span>
                    {pkg?.amount ? <span>{formatCurrencyPlacement(
                      formatNumber(pkg?.amount),
                      currencySymbol
                    )}</span> : <span>-</span>}
                  </div>
                </div>
              ))}
              {activePayment && (
                <>
                  <div
                    className="d-flex justify-content-between"
                    style={{
                      borderTop: `1px solid ${border[theme]}`,
                      fontWeight: 600,
                      fontSize: '1.125rem',
                      paddingTop: '1rem',
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
                      marginBottom: '0.25rem',
                      color: textValue[theme],
                    }}
                  >
                    <span>{t('Payment Method')}</span>
                    <span>
                      {t(detailData?.payment_details?.payment_method) || '-'}
                    </span>
                  </div>
                </>
              )}
            </FormBlock>
          </Box>
        </Box>
      )}
      <CenterBtn
        color="secondary"
        type="button"
        variant="outline"
        size="lg"
        onClick={onHide}
        label={t('Close')}
      />
    </CustomModal>
  );
}
