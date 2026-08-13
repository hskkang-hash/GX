import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CenterBtn,
  CustomModal,
  FormBlock,
  useActivePayment,
  useTheme,
} from 'rj-core';

import { TabItem, Tabs } from '../../../../../../components/Form/Tabs';
import { useReadyToShipTab } from '../ReadyToShipTab/hooks/useReadyToShipTab';
import './OrderDetailModal.scss';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import { formatCurrency, useFormatCurrencyPlacement } from '@/utils/formatCurrency';
import { useFormatNumber } from '@/utils/formatConfig';

type Measurement = {
  value?: number | string;
  unit?: string;
};

interface OrderItem {
  weight?: Measurement;
  dimension_l?: Measurement;
  dimension_w?: Measurement;
  dimension_h?: Measurement;
  item_type__name?: string;
  quantity?: number;
  is_fragile?: boolean;
  is_waterproof?: boolean;
}

interface PaymentDetails {
  amount?: number | string;
}

interface OrderDetail {
  sender_name?: string;
  sender_phone?: string;
  sender_address?: string;
  sender_note?: string;
  recipient_name?: string;
  recipient_phone?: string;
  recipient_address?: string;
  recipient_note?: string;
  order_code?: string;
  created_on?: string;
  origin?: string;
  destination?: string;
  payment_details?: PaymentDetails;
  items?: OrderItem[];
  financial_summary?: any;
}

interface OrderDetailModalV2Props {
  show: boolean;
  onHide: () => void;
  detailData?: OrderDetail;
  hasTabs?: boolean;
  orderIds?: number[];
}

// modal detail for order detail Ready to Ship
const OrderDetailModalV2 = ({
  show,
  onHide,
  detailData,
  hasTabs = false,
  orderIds = [],
}: OrderDetailModalV2Props): React.ReactElement => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [tabs, setTabs] = useState<TabItem[]>([]);
  const activePayment = useActivePayment();
  const { converRawDateToDateTimeFormat } = useConvertDate();
  const { getDetailOrder } = useReadyToShipTab();
  const { currencySymbol } = formatCurrency();
  const { formatNumber } = useFormatNumber();
  const { format: formatCurrencyPlacement } = useFormatCurrencyPlacement();
  const totalAmountFormat = formatCurrencyPlacement(
    formatNumber(detailData?.financial_summary?.total_amount?.value),
    currencySymbol
  );

  useEffect(() => {
    let isCancelled = false;

    const loadTabsData = async (): Promise<void> => {
      if (hasTabs && show && orderIds.length > 0) {
        try {
          const results = await Promise.all(
            orderIds.map((orderId) => getDetailOrder(orderId)),
          );
          if (isCancelled) return;
          const nextTabs: TabItem[] = results.map((res) => ({
            label: res.data.order_code,
            content: <ContentOrderDetail detailData={res.data} />,
          }));
          setTabs(nextTabs);
        } catch (_error) {
          if (!isCancelled) {
            setTabs([]);
          }
        }
      } else {
        if (!isCancelled) {
          setTabs((prevTabs) => (prevTabs.length > 0 ? [] : prevTabs));
        }
      }
    };

    loadTabsData();

    return () => {
      isCancelled = true;
    };
  }, [hasTabs, show, orderIds]); // eslint-disable-line react-hooks/exhaustive-deps

  const ContentOrderDetail = ({
    detailData,
  }: {
    detailData?: OrderDetail;
  }): React.ReactElement => {
    console.log('detailData', detailData);
    const items: OrderItem[] = detailData?.items ?? [];
    return (
      <div
        style={{
          display: 'grid',
          gap: '1rem',
          padding: '0rem 1rem 0 1rem',
          overflow: 'auto',
          scrollbarWidth: 'thin',
          maxHeight: '75vh',
          marginBottom: '1rem',
        }}
      >
        <FormBlock
          style={{
            backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
          }}
        >
          <div className="header-title">{t('Sender')}</div>
          <FormBlock
            style={{
              display: 'grid',
              gap: '1rem',
              gridTemplateColumns: '1fr 1fr',
            }}
          >
            <div>
              <div className="label">{t('Name')}</div>
              <span className="value">{detailData?.sender_name || '-'}</span>
            </div>
            <div>
              <div className="label">{t('Phone')}</div>
              <span className="value">{detailData?.sender_phone || '-'}</span>
            </div>
            <div style={{ gridColumn: 'span 2' }}>
              <div className="label">{t('Address')}</div>
              <span className="value">{detailData?.origin || '-'}</span>
            </div>
            <div style={{ gridColumn: 'span 2' }}>
              <div className="label">{t('Note')}</div>
              <span className="value">{detailData?.sender_note || '-'}</span>
            </div>
          </FormBlock>
        </FormBlock>
        <FormBlock
          style={{
            backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
          }}
        >
          <div className="header-title">{t('Recipient')}</div>
          <FormBlock
            style={{
              display: 'grid',
              gap: '1rem',
              gridTemplateColumns: '1fr 1fr',
            }}
          >
            <div>
              <div className="label">{t('Name')}</div>
              <span className="value">{detailData?.recipient_name || '-'}</span>
            </div>
            <div>
              <div className="label">{t('Phone')}</div>
              <span className="value">
                {detailData?.recipient_phone || '-'}
              </span>
            </div>
            <div style={{ gridColumn: 'span 2' }}>
              <div className="label">{t('Address')}</div>
              <span className="value">
                {detailData?.recipient_address || '-'}
              </span>
            </div>
            <div style={{ gridColumn: 'span 2' }}>
              <div className="label">{t('Note')}</div>
              <span className="value">{detailData?.recipient_note || '-'}</span>
            </div>
          </FormBlock>
        </FormBlock>
        <FormBlock
          style={{
            backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
          }}
        >
          <div className="header-title pb-3">{t('Order Information')}</div>
          <FormBlock
            style={{
              display: 'grid',
              gap: '1rem',
              gridTemplateColumns: '1fr 1fr',
            }}
          >
            <div>
              <div className="label">{t('Order ID')}</div>
              <span className="value">{detailData?.order_code || '-'}</span>
            </div>
            <div>
              <div className="label">{t('Order Time')}</div>
              <span className="value">{converRawDateToDateTimeFormat(detailData?.created_on) || '-'}</span>
            </div>
            <div>
              <div className="label">{t('Origin')}</div>
              <span className="value">{detailData?.origin || '-'}</span>
            </div>
            <div>
              <div className="label">{t('Destination')}</div>
              <span className="value">{detailData?.destination || '-'}</span>
            </div>
          </FormBlock>
        </FormBlock>
        {activePayment && (
          <FormBlock
            style={{
              backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
            }}
          >
            <div className="header-title pb-3">{t('Payment Information')}</div>
            <FormBlock
              style={{
                display: 'grid',
                gap: '1rem',
              }}
            >
              <div style={{ gridColumn: 'span 2' }}>
                <div className="label">{t('Total Amount')}</div>
                <span className="value">
                  {totalAmountFormat ||
                    '-'}
                </span>
              </div>
            </FormBlock>
          </FormBlock>
        )}
        {items.length > 0 &&
          items.map((item: OrderItem, index: number) => (
            <FormBlock
              key={`order-item-${index}`}
              style={{
                backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
              }}
            >
              <div className="header-title pb-3">
                {t('Package')} {index + 1}
              </div>
              <FormBlock
                style={{
                  display: 'grid',
                  gap: '1rem',
                  gridTemplateColumns: '1fr 1fr 1fr',
                }}
              >
                <div>
                  <div className="label">{t('Weight')}</div>
                  <span className="value">
                    {item.weight?.value
                      ? `${item.weight?.value}${item.weight?.unit ?? ''}`
                      : '-'}
                  </span>
                </div>
                <div>
                  <div className="label">{t('Dimensions')}</div>
                  <span className="value">
                    {item?.dimension_l?.value &&
                      item?.dimension_w?.value &&
                      item?.dimension_h?.value
                      ? `${item?.dimension_l?.value}${item?.dimension_l?.unit ?? ''} x ${item?.dimension_w?.value}${item?.dimension_w?.unit ?? ''} x ${item?.dimension_h?.value}${item?.dimension_h?.unit ?? ''}`
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

  if (hasTabs) {
    return (
      <CustomModal
        id="order-detail-modal"
        title={t('Order Detail')}
        show={show}
        onHide={onHide}
      >
        <Tabs items={tabs} />
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

  return (
    <CustomModal
      id="order-detail-modal"
      title={t('Order Detail')}
      show={show}
      onHide={onHide}
    >
      <ContentOrderDetail detailData={detailData} />
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
};

export default React.memo(OrderDetailModalV2);
