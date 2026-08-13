import { FormBlock, useActivePayment } from 'rj-core';

import './DetailReceived.scss';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import { formatCurrency, formatCurrencyPlacement, useFormatCurrencyPlacement } from '@/utils/formatCurrency';
import { useFormatNumber } from '@/utils/formatConfig';

export const DetailReceived = ({
  t,
  theme,
  dataDetail,
  totalAmount,
}: {
  t: any;
  theme: any;
  dataDetail: any;
  totalAmount: string;
}) => {
  const activePayment = useActivePayment();
  const { converRawDateToDateTimeFormat } = useConvertDate();
  const { currencySymbol } = formatCurrency();
  const { formatNumber } = useFormatNumber();
  const { format: formatCurrencyPlacement } = useFormatCurrencyPlacement();
  const totalAmountFormat = formatCurrencyPlacement(
    formatNumber(dataDetail?.financial_summary?.total_amount?.value),
    currencySymbol
  );
  return (
    <div
      style={{ display: 'grid', gap: '1rem', gridTemplateColumns: '1fr 1fr' }}
      id="detail-received"
    >
      <FormBlock>
        <div className="header-title">{t('Sender')}</div>
        <FormBlock
          style={{
            display: 'grid',
            gap: '1rem',
            gridTemplateColumns: '1fr 1fr',
            backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
          }}
        >
          <div>
            <div className="label">{t('Name')}</div>
            <span className="value">{dataDetail?.sender_name || '-'}</span>
          </div>
          <div>
            <div className="label">{t('Phone')}</div>
            <span className="value">{dataDetail?.sender_phone || '-'}</span>
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <div className="label">{t('Address')}</div>
            <span className="value">
              {dataDetail?.sender_address__full_address || '-'}
            </span>
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <div className="label">{t('Note')}</div>
            <span className="value">{dataDetail?.sender_note || '-'}</span>
          </div>
        </FormBlock>
      </FormBlock>
      <FormBlock>
        <div className="header-title pb-3">{t('Recipient')}</div>
        <FormBlock
          style={{
            display: 'grid',
            gap: '1rem',
            gridTemplateColumns: '1fr 1fr',
            backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
          }}
        >
          <div>
            <div className="label">{t('Name')}</div>
            <span className="value">{dataDetail?.recipient_name || '-'}</span>
          </div>
          <div>
            <div className="label">{t('Phone')}</div>
            <span className="value">{dataDetail?.recipient_phone || '-'}</span>
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <div className="label">{t('Address')}</div>
            <span className="value">
              {dataDetail?.recipient_address || '-'}
            </span>
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <div className="label">{t('Note')}</div>
            <span className="value">{dataDetail?.recipient_note || '-'}</span>
          </div>
        </FormBlock>
      </FormBlock>
      <FormBlock>
        <div className="header-title pb-3">{t('Order Information')}</div>
        <FormBlock
          style={{
            display: 'grid',
            gap: '1rem',
            gridTemplateColumns: '1fr 1fr',
            backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
          }}
        >
          <div>
            <div className="label">{t('Order ID')}</div>
            <span className="value">{dataDetail?.order_code || '-'}</span>
          </div>
          <div>
            <div className="label">{t('Order Time')}</div>
            <span className="value">{converRawDateToDateTimeFormat(dataDetail?.created_on) || '-'}</span>
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <div className="label">{t('Delivery Hub')}</div>
            <span className="value">{dataDetail?.origin || '-'}</span>
          </div>
          <div style={{ gridColumn: 'span 2' }}>
            <div className="label">{t('Delivery Point')}</div>
            <span className="value">{dataDetail?.destination || '-'}</span>
          </div>
        </FormBlock>
      </FormBlock>
      {activePayment && (
        <FormBlock>
          <div className="header-title pb-3">{t('Payment Information')}</div>
          <FormBlock
            style={{
              display: 'grid',
              gap: '1rem',
              gridTemplateColumns: '1fr 1fr',
              backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
            }}
          >
            <div style={{ gridColumn: 'span 2' }}>
              <div className="label">{t('Total Amount')}</div>
              <span className="value">{totalAmountFormat}</span>
            </div>
          </FormBlock>
        </FormBlock>
      )}
      {dataDetail?.items?.length > 0 &&
        dataDetail?.items.map((item: any, index: number) => (
          <FormBlock>
            <div className="header-title pb-3">{t(`Package ${index + 1}`)}</div>
            <FormBlock
              style={{
                display: 'grid',
                gap: '1rem',
                gridTemplateColumns: '1fr 1fr 1fr',
                backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
              }}
            >
              <div>
                <div className="label">{t('Weight')}</div>
                <span className="value">
                  {(item?.weight?.value ?? 0) +
                    ' ' +
                    (item?.weight?.unit || '')}
                </span>
              </div>
              <div>
                <div className="label">{t('Dimensions')}</div>
                <span className="value">
                  {item?.dimension_l?.value &&
                    item?.dimension_w?.value &&
                    item?.dimension_h?.value
                    ? item?.dimension_l?.value +
                    item?.dimension_l?.unit +
                    ' x ' +
                    item?.dimension_w?.value +
                    item?.dimension_w?.unit +
                    ' x ' +
                    item?.dimension_h?.value +
                    item?.dimension_h?.unit
                    : '-'}
                </span>
              </div>
              <div>
                <div className="label">{t('Item Type')}</div>
                <span className="value">{item?.item_type__name || '-'}</span>
              </div>
              <div>
                <div className="label">{t('Quantity')}</div>
                <span className="value">{item?.quantity || '-'}</span>
              </div>
              <div>
                <div className="label">{t('Fragile')}</div>
                <span className="value">
                  {item?.is_fragile ? t('Yes') : t('No')}
                </span>
              </div>
              <div>
                <div className="label">{t('Waterproof')}</div>
                <span className="value">
                  {item?.is_waterproof ? t('Yes') : t('No')}
                </span>
              </div>
            </FormBlock>
          </FormBlock>
        ))}
    </div>
  );
};
