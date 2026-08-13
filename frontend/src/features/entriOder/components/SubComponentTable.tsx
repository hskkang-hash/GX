import { t } from 'i18next';
import { BsDash } from 'react-icons/bs';

import '@/features/entriOder/assets/scss/SubComponentTable.scss';

interface SubComponentTableProps {
  row: {
    originalSubRows?: {
      id?: string;
      another_info?: {
        etri?: {
          receipt_id?: string;
          tracking_number?: string;
        };
      };
      sender_name?: string;
      sender_phone?: string;
      sender_address__full_address?: string;
      created_on?: string;
      completed_time?: string;
      recipient_name?: string;
      recipient_phone?: string;
      items?: Array<{
        item_type__name?: string;
        weight?: { value?: number };
        dimension_w?: { value?: number };
        dimension_h?: { value?: number };
        dimension_l?: { value?: number };
      }>;
      recipient_note?: string;
      status__name?: string;
      recipient_address__full_address?: string;
      delivered_time?: string;
      returned_time?: string;
      cancel_time?: string;
    };
  };
}

const SubComponentTable: React.FC<SubComponentTableProps> = ({ row }) => {
  const resultData = {
    key: row.originalSubRows?.id,
    receipt_number: row.originalSubRows?.another_info?.etri?.receipt_id,
    waybill_number: row.originalSubRows?.another_info?.etri?.tracking_number,
    sender_name: row.originalSubRows?.sender_name,
    sender_phone: row.originalSubRows?.sender_phone,
    sender_address: row.originalSubRows?.sender_address__full_address,
    received_date: row.originalSubRows?.created_on,
    completed_date: row.originalSubRows?.completed_time,
    recipient_name: row.originalSubRows?.recipient_name,
    recipient_phone: row.originalSubRows?.recipient_phone,
    type_of_item: row.originalSubRows?.items?.[0]?.item_type__name,
    weight: row.originalSubRows?.items?.[0]?.weight?.value,
    note: row.originalSubRows?.recipient_note,
    status: row.originalSubRows?.status__name,
    width: row.originalSubRows?.items?.[0]?.dimension_w?.value,
    height: row.originalSubRows?.items?.[0]?.dimension_h?.value,
    length: row.originalSubRows?.items?.[0]?.dimension_l?.value,
    recipient_address: row.originalSubRows?.recipient_address__full_address,
    delivered_time: row.originalSubRows?.delivered_time,
    cancel_time: row.originalSubRows?.cancel_time,
  };
  if (!row.originalSubRows) {
    return <div>{t('Loading')}...</div>;
  }

  return (
    <>
      <div className="shipment-table">
        <table>
          <tbody>
            <tr>
              <th>{t('Receipt Number')}</th>
              <td colSpan={3}>{resultData.receipt_number || <BsDash />}</td>
              <th>{t('Date Received')}</th>
              <td colSpan={3}>{resultData.received_date || <BsDash />}</td>
              <th colSpan={2}>{t('entri_order.Item Type')}</th>
              <td colSpan={2}>{resultData.type_of_item || <BsDash />}</td>
              <th colSpan={2}>{t('entri_order.Item Weight (Kg)')}</th>
              <td colSpan={2}>{resultData.weight || <BsDash />}</td>
            </tr>
            <tr>
              <th>{t('Tracking Number')}</th>
              <td colSpan={3}>{resultData.waybill_number || <BsDash />}</td>
              <th>{t('Delivery/Cancel Date')}</th>
              <td colSpan={3}>
                {resultData.delivered_time ? (
                  resultData.delivered_time
                ) : resultData.cancel_time ? (
                  resultData.cancel_time
                ) : (
                  <BsDash />
                )}
              </td>
              <th colSpan={2}>{t('entri_order.Note')}</th>
              <td colSpan={6}>{resultData.note || '-'}</td>
            </tr>
            <tr>
              <th>{t('Sender')}</th>
              <td>{resultData.sender_name || <BsDash />}</td>
              <td
                className="phone-cell"
                colSpan={2}
              >
                {resultData.sender_phone || <BsDash />}
              </td>
              <th>{t('Recipient')}</th>
              <td>{resultData.recipient_name || <BsDash />}</td>
              <td
                className="phone-cell"
                colSpan={2}
              >
                {resultData.recipient_phone || <BsDash />}
              </td>
              <th colSpan={2}>{t('entri_order.Item Dimensions (cm)')}</th>
              <th className="fw-semibold">{t('Width')}</th>
              <td>{resultData.width || <BsDash />}</td>
              <th className="fw-semibold">{t('Length')}</th>
              <td>{resultData.length || <BsDash />}</td>
              <th className="fw-semibold">{t('Height')}</th>
              <td>{resultData.height || <BsDash />}</td>
            </tr>
            <tr>
              <th>{t('entri_order.Sender Address')}</th>
              <td colSpan={7}>{resultData.sender_address || <BsDash />}</td>
              <th colSpan={2}>{t('entri_order.Recipient Address')}</th>
              <td colSpan={5}>{resultData.recipient_address || <BsDash />}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </>
  );
};

export default SubComponentTable;
