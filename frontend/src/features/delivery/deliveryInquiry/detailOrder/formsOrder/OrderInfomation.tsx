import { Box } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { FormBlock, useActivePayment, useTheme } from 'rj-core';

import Colors from '@/configs/Colors';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import { useFormatNumber } from '@/utils/formatConfig';
import {
  formatCurrency,
  useFormatCurrencyPlacement,
} from '@/utils/formatCurrency';

import { formatStatusDeliveryInquiry } from '../../utils/StatusColorInquiry';

const OrderInformation = ({ dataDetail }: { dataDetail: any }) => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const activePayment = useActivePayment();
  const { converRawDateToDateTimeFormat } = useConvertDate();
  const { currencySymbol } = formatCurrency();
  const { formatNumber } = useFormatNumber();
  const { format: formatCurrencyPlacement } = useFormatCurrencyPlacement();

  const totalAmount = formatCurrencyPlacement(
    formatNumber(dataDetail?.financial_summary?.total_amount?.value),
    currencySymbol,
  );
  const penddingPayment = [
    { id: 1, name: t('Order ID'), value: dataDetail?.order_code, label: 'all' },
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
          {dataDetail?.mapped_status_list?.map(
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
          )}
        </div>
      ),
      label: 'all',
    },
    {
      id: 3,
      name: 'Order Time',
      value: dataDetail?.created_on
        ? converRawDateToDateTimeFormat(dataDetail?.created_on)
        : '-',
      label: 'all',
    },
    {
      id: 4,
      name: 'Payment Time',
      value: dataDetail?.paid_time
        ? converRawDateToDateTimeFormat(dataDetail?.paid_time)
        : '-',
      label: 'payment_time',
    },
    {
      id: 5,
      name: 'Order Verification Time',
      value: dataDetail?.verified_time
        ? converRawDateToDateTimeFormat(dataDetail?.verified_time)
        : '-',
      label: 'order_verification',
    },
  ];
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

  return (
    <Box
      sx={{
        display: 'grid',
        gap: '24px',
        gridTemplateColumns: '8fr 4fr',
        alignItems: 'start',
      }}
    >
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
            {penddingPayment.map((item) => (
              <Box
                key={item.id}
                sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}
              >
                <span>{t(item.name)}</span>
                <span>{item.value}</span>
              </Box>
            ))}
          </Box>
        </FormBlock>
        <FormBlock>
          <div
            className="d-flex flex-column"
            style={{ gap: '16px' }}
          >
            {senderAndRecipientData.map((item, index) => (
              <div
                key={item.id}
                style={{ padding: '3px' }}
              >
                <div className="header-title pb-3">{t(item.title)}</div>
                <div className="d-flex flex-column gap-3">
                  <ul
                    className="d-flex flex-column rounded-3 list-unstyled"
                    style={{
                      backgroundColor:
                        theme === 'dark' ? Colors.Gray7 : '#F6F7F8',
                      paddingLeft: '12px',
                      paddingRight: '12px',
                      marginBottom: 0,
                    }}
                  >
                    {item.list_item
                      .filter((i) => i.value != null)
                      .map((listItem, listIndex) => (
                        <li
                          key={listIndex}
                          style={{ paddingTop: '8px', paddingBottom: '8px' }}
                          className={`d-flex justify-content-between ${listIndex === item.list_item.filter((i) => i.value != null).length - 1 ? '' : 'border-bottom'}`}
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
            <div className="header-title pb-3">{t('Invoice')}</div>
            {packageData?.map((item: any, index: number) => {
              if (!item) return null;
              if (!item.list_item) return null;
              return (
                <div key={item.id}>
                  <div className="d-flex flex-column gap-3">
                    <div className="d-flex justify-content-between">
                      <span>1 x {t('Package')}</span>
                      <span>
                        {formatCurrencyPlacement(
                          formatNumber(item?.price),
                          currencySymbol,
                        )}
                      </span>
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
                      {item.list_item.map((item: any, index: number) => {
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
                    hidden={!activePayment && packageData.length - 1 === index}
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
                  <span>{totalAmount}</span>
                </div>
                <div className="d-flex justify-content-between header-title pb-0">
                  <span>{t('Payment Method')}</span>
                  <span>
                    {t(dataDetail?.payment_details?.payment_method || '-')}
                  </span>
                </div>
              </div>
            )}
          </Box>
        </FormBlock>
      </div>
    </Box>
  );
};
export default OrderInformation;
