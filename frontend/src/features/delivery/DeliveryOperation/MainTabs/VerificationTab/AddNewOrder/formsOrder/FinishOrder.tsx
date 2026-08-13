import React from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { CustomBtn, useTheme, ToastTopHelper } from 'rj-core';

import CopyIcon from '@/assets/images/CopyIcon';
import AwaitingPaymentDark from '@/assets/images/awaiting-payment-dark.svg';
import AwaitingPayment from '@/assets/images/awaiting-payment.svg';
import FailPaymentDark from '@/assets/images/fail-payment-dark.svg';
import FailPayment from '@/assets/images/fail-payment.svg';
import SuccessPaymentDark from '@/assets/images/success-payment-dark.svg';
import SuccessPayment from '@/assets/images/success-payment.svg';
import { CustomRoutes } from '@/services/API';

const FinishOrder = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { watch } = useFormContext();
  const dataAfterSubmit = watch('data.orderAfterSubmit');
  console.log({ dataAfterSubmit });
  const status = dataAfterSubmit?.status_code;

  const handleCopy = (content: string) => {
    try {
      navigator.clipboard.writeText(content);
      ToastTopHelper.success(t('Copied to clipboard'));
    } catch (error) {
      console.error('Unable to copy to clipboard:', error);
    }
  };

  const PaymentStatus = {
    pending_confirmation: {
      image: theme === 'dark' ? SuccessPaymentDark : SuccessPayment,
      title: 'Thank you! Your order has been successfully placed.',
      orderId: t('Order ID') + ': ' + '#' + dataAfterSubmit?.order_code,
      description:
        'Our team is now processing your order and will ensure a swift and smooth delivery.',
      buttons: [
        {
          label: t('Back to Delivery Operation'),
          onClick: () => navigate(CustomRoutes.deliveryOperation.path),
        },
      ],
    },
    payment_failed: {
      image: theme === 'dark' ? FailPaymentDark : FailPayment,
      title: 'Payment Failed',
      orderId: t('Order ID') + ': ' + '#' + dataAfterSubmit?.order_code,
      description:
        t(
          'Your order was placed but the payment failed. Please complete your payment to confirm the order. If payment isn’t received within',
        ) +
        ' [XX] ' +
        t('minutes') +
        ',' +
        ' ' +
        t('your order will be automatically canceled.'),
      buttons: [
        {
          label: t('Back to Delivery Operation'),
          onClick: () => navigate(CustomRoutes.deliveryOperation.path),
          isOutline: true,
        },
        {
          label: t('Pay Again'),
          isStyle: true,
          onClick: () => navigate('/'),
        },
      ],
    },
    awaiting_payment: {
      image: theme === 'dark' ? AwaitingPaymentDark : AwaitingPayment,
      title: 'Order Placed – Awaiting Payment',
      orderId: t('Order ID') + ': ' + '#' + dataAfterSubmit?.order_code,
      description:
        'Your order has been placed and is waiting for payment. We’ll process it once the payment is completed.',
      buttons: [
        {
          label: t('Back to Delivery Operation'),
          onClick: () => navigate(CustomRoutes.deliveryOperation.path),
        },
      ],
    },
  };
  const data = PaymentStatus[status as keyof typeof PaymentStatus];

  return (
    <div
      style={{ marginTop: '6.219rem' }}
      className="finish-order"
    >
      <div className="finish-order__content">
        <img
          style={{ marginBottom: '3rem' }}
          src={data?.image}
          className="h-full w-full object-cover"
          alt="payment-status"
        />
        <div
          style={{ gap: '8px' }}
          className="d-flex flex-column"
        >
          <span className="header-text">{t(data?.title)}</span>
          <div className="order-id">
            {data?.orderId}
            <div
              className="cursor-pointer"
              onClick={() => handleCopy(data?.orderId.split('#')[1])}
            >
              {' '}
              <CopyIcon color={theme === 'dark' ? '#1EA1EB' : '#1D9BE2'} />
            </div>
          </div>
          <p className="order-description">{t(data?.description)}</p>
        </div>
        <div className="d-flex gap-3 mt-4">
          {data?.buttons.map((btn, idx) => (
            <CustomBtn
              key={idx}
              label={btn.label}
              variant={btn.isOutline ? 'outline' : 'contained'}
              color="primary"
              style={
                btn.isStyle
                  ? {
                      height: '3.109rem',
                      paddingLeft: '4.975rem',
                      paddingRight: '4.975rem',
                    }
                  : { height: '3.109rem' }
              }
              type="button"
              onClick={btn.onClick}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default FinishOrder;
