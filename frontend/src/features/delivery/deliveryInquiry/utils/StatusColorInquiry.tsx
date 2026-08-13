import ButtonStatus from '../components/ButtonStatus';

export const statusInformationInquiry = {
  received: {
    color: '#683DE2',
    border: '1px solid #683DE2',
    backgroundColor: 'transparent',
    backgroundColorNotification: '#F4E7FF',
    titleNotification: 'Order Received',
  },
  awaiting_delivery: {
    color: '#F0C418',
    border: '1px solid #F0C418',
    backgroundColor: 'transparent',
    backgroundColorNotification: '#FDF5D7',
    titleNotification: 'Awaiting Delivery',
  },
  in_transit: {
    color: '#1D9BE2',
    border: '1px solid #1D9BE2',
    backgroundColor: 'transparent',
    backgroundColorNotification: '#EEF9FF',
    titleNotification: 'Delivery Started',
  },
  delivered: {
    color: '#0CBA47',
    border: '1px solid #0CBA47',
    backgroundColor: 'transparent',
    backgroundColorNotification: '#D6F8E2',
    titleNotification: 'Order Delivered',
  },
  cancelled: {
    color: '#EE533D',
    border: '1px solid #EE533D',
    backgroundColor: 'transparent',
    backgroundColorNotification: '#FFEBE8',
    titleNotification: 'Order Cancelled',
  },
  returned: {
    color: '#9C9D9D',
    border: '1px solid #9C9D9D',
    backgroundColor: 'transparent',
    backgroundColorNotification: '',
    titleNotification: 'Order Returned',
  },
  awaiting_payment: {
    color: '#683DE2',
    border: '1px solid #683DE2',
    backgroundColor: 'transparent',
    backgroundColorNotification: '',
    titleNotification: 'Awaiting Payment',
  },
  awaiting_shipment: {
    color: '#F0C418',
    border: '1px solid #F0C418',
    backgroundColor: 'transparent',
    backgroundColorNotification: '#FDF5D7',
    titleNotification: 'Awaiting Delivery',
  },
  select_route_processing: {
    color: '#F0C418',
    border: '1px solid #F0C418',
    backgroundColor: 'transparent',
    backgroundColorNotification: '#FDF5D7',
    titleNotification: 'Select Route Processing',
  },
};

type FormatStatusDeliveryInquiryParams = {
  t: (key: string) => string;
  status_name: string;
  status_code: string;
  backgroundColor?: string;
  color?: string;
  border?: string;
  onClickAwaitingDelivery?: () => void;
  onClickCancelled?: () => void;
  isShowButton?: boolean;
};

export const StatusAfterArrived = [
  'receipt_cancelled',
  'completed_order',
  'in_transit_processing',
  'returned_order',
  'arrived_order',
  'cancelled',
  'order_due_for_returned',
  'order_pending_returned',
  'overdue_order',
];

export const formatStatusDeliveryInquiry = ({
  t,
  status_name,
  status_code,
  backgroundColor,
  color,
  border,
  onClickAwaitingDelivery,
  onClickCancelled,
  isShowButton = true,
}: FormatStatusDeliveryInquiryParams): React.ReactNode => {
  if (status_code === 'unverified_order' && isShowButton) {
    return (
      <ButtonStatus
        key={`${status_code}-${status_name}`}
        color={color}
        backgroundColor={backgroundColor}
        border={border}
        items={[
          {
            label: t('Awaiting Delivery'),
            key: 'awaiting_delivery',
            onClick: onClickAwaitingDelivery,
          },
          {
            label: t('Cancelled'),
            key: 'cancelled',
            onClick: onClickCancelled,
          },
        ]}
        label={t(status_name)}
      />
    );
  }

  if (!StatusAfterArrived.includes(status_code) && isShowButton) {
    return (
      <ButtonStatus
        key={status_code}
        color={color}
        backgroundColor={backgroundColor}
        border={border}
        items={[
          {
            label: t('Cancelled'),
            key: 'cancelled',
            onClick: onClickCancelled,
          },
        ]}
        label={t(status_name)}
      />
    );
  }
  return (
    <span
      key={status_code}
      className="status-style"
      style={{
        backgroundColor: backgroundColor,
        color: color,
        border: border,
        width: 'fit-content',
      }}
    >
      {t(status_name)}
    </span>
  );
};
