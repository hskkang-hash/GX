import { useTranslation } from 'react-i18next';

import { statusInformationInquiry } from './StatusColorInquiry';

type StatusCode = keyof typeof statusInformationInquiry;

interface OrderSubset {
  order_code: string | number;
  recipient_name: string | number;
  'pickup_location.city_county_district': string;
  'recipient_address.city': string;
}

interface Message {
  order: OrderSubset;
  new_status: { code: StatusCode };
  timestamp: string | number | Date;
}

interface ConvertedMessage {
  title: string;
  description: {
    time: string;
    transport_route: string;
    order_code: string | number;
    recipient_name: string | number;
  };
  color: string;
  backgroundColor: string;
}

const formatTime = (input: number | Date | string): string => {
  const date =
    typeof input === 'number' || typeof input === 'string'
      ? new Date(input)
      : input;
  const ms = date.getTime();
  if (Number.isNaN(ms)) return '';
  const hh = String(date.getHours()).padStart(2, '0');
  const mm = String(date.getMinutes()).padStart(2, '0');
  const ss = String(date.getSeconds()).padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
};

export default function convertInfoNotification(
  t: any,
  message: Message,
): ConvertedMessage {
  const { order, new_status, timestamp } = message;
  const { code: new_status_code } = new_status;

  const formattedTime = formatTime(timestamp);

  const convertedMessage: ConvertedMessage = {
    title: t(
      statusInformationInquiry[
        new_status_code as keyof typeof statusInformationInquiry
      ].titleNotification,
    ),
    description: {
      time: formattedTime,
      transport_route: `${order['pickup_location.city_county_district'] ? order['pickup_location.city_county_district'] : ''} -> ${order['recipient_address.city'] ? order['recipient_address.city'] : ''} [${t(
        statusInformationInquiry[
          new_status_code as keyof typeof statusInformationInquiry
        ].titleNotification,
      )}]`,
      order_code: order.order_code,
      recipient_name: order.recipient_name,
    },
    color:
      statusInformationInquiry[
        new_status_code as keyof typeof statusInformationInquiry
      ]?.color,
    backgroundColor:
      statusInformationInquiry[
        new_status_code as keyof typeof statusInformationInquiry
      ]?.backgroundColorNotification,
  };

  return convertedMessage;
}
