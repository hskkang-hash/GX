import { Box } from '@mui/material';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { FormBlock, useTheme } from 'rj-core';

import Colors from '@/configs/Colors';
import { formatCurrency, useFormatCurrencyPlacement } from '@/utils/formatCurrency';
import { formatNumber } from '@/utils/formatNumberUtils';

const PaymentOrder = () => {
  const { register, watch, setValue } = useFormContext();
  const [theme] = useTheme();
  const { t } = useTranslation();
  const payment = watch('data.payment');
  const package_info = watch('data.package');
  const { currencySymbol } = formatCurrency();
  const { format: formatCurrencyPlacement } = useFormatCurrencyPlacement();

  const packageData = package_info.map((item: any, index: number) => {
    return {
      id: index + 1,
      price: formatNumber(item?.amount) || formatNumber('10000'),
      list_item: [
        {
          name: t('Weight'),
          value:
            (item?.package_weight?.value ?? 0) +
            ' ' +
            item?.package_weight?.unit,
        },
        {
          name: t('Dimensions'),
          value:
            item?.dimensions?.length?.value +
            ' ' +
            item?.dimensions?.length?.unit +
            ' x ' +
            item?.dimensions?.width?.value +
            ' ' +
            item?.dimensions?.width?.unit +
            ' x ' +
            item?.dimensions?.height?.value +
            ' ' +
            item?.dimensions?.height?.unit,
        },
        {
          name: t('Item Type'),
          value: item?.item_type?.value?.label,
        },
        {
          name: t('Waterproof'),
          value: item?.is_water_proof && t('Yes'),
        },
        {
          name: t('Fragile'),
          value: item?.is_fragile && t('Yes'),
        },
        {
          name: t('Packaging'),
          value: item?.packaging?.value?.label,
        },
        {
          name: t('Note'),
          value: item?.note,
        },
      ],
    };
  });

  const paymentOptions = [
    {
      id: 1,
      name: t('Cash'),
      value: 'cash',
    },
    {
      id: 2,
      name: t('KaKao Pay'),
      value: 'kakao_pay',
      isDisabled: true,
    },
    {
      id: 3,
      name: t('Credit Card / Debit Card'),
      value: 'credit_debit_card',
      isDisabled: true,
    },
    {
      id: 4,
      name: t('Bank Transfer / Wire Transfer'),
      value: 'bank_wire_transfer',
      isDisabled: true,
    },
  ];

  return (
    <Box
      sx={{
        display: 'grid',
        gap: '12px',
        gridTemplateColumns: '8fr 4fr',
      }}
    >
      <FormBlock>
        <div className="header-title pb-3">{t('Payment Detail')}</div>
        <div className="d-flex flex-column gap-3">
          {paymentOptions.map((option) => (
            <div
              title={
                option.isDisabled ? t('This feature is not available') : ''
              }
              key={option.id}
              onClick={() => {
                if (option.isDisabled) return;
                setValue('data.payment', option.value);
              }}
              style={{
                backgroundColor: theme === 'dark' ? Colors.Gray7 : Colors.Gray1,
                border: `1px solid  ${theme === 'dark' ? Colors.Gray6 : Colors.Gray4}`,
              }}
              className={`d-flex align-items-center cursor-pointer gap-2 p-3 rounded-3 ${option.isDisabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <input
                type="radio"
                id={option.value}
                name="data.payment"
                value={option.value}
                className={`checkbox-payment ${option.isDisabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
                checked={payment === option.value}
                {...register('data.payment')}
                disabled={option.isDisabled}
              />
              <label htmlFor={option.value}>{option.name}</label>
            </div>
          ))}
        </div>
      </FormBlock>
      <FormBlock>
        <div className="header-title pb-3">{t('Invoice')}</div>
        {packageData.map((item, index) => (
          <div key={item.id}>
            <div className="d-flex flex-column gap-3">
              <div className="d-flex justify-content-between">
                <span>1 x {t('Package')}</span>
                <span>{formatCurrencyPlacement(item.price, currencySymbol)}</span>
              </div>
              <ul
                style={{
                  backgroundColor: theme === 'dark' ? Colors.Gray7 : '#F6F7F8',
                  padding: '10px',
                  marginBottom: 0,
                }}
                className="d-flex flex-column gap-2 rounded-3 list-unstyled"
              >
                {item.list_item.map((item, index) => {
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
                      <span>{item.value}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
            <hr style={{ marginTop: 15, marginBottom: 15 }} />
          </div>
        ))}
        <div className="d-flex justify-content-between header-title pb-0">
          <span>{t('Total')}</span>
          <span>{formatCurrencyPlacement(formatNumber('10000'), currencySymbol)}</span>
        </div>
      </FormBlock>
    </Box>
  );
};

export default PaymentOrder;
