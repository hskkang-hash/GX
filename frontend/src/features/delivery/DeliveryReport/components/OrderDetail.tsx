import { Box, CircularProgress } from '@mui/material';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useSearchParams } from 'react-router-dom';
import { useTheme } from 'rj-core';

import API, { endpoint } from '@/services/API';

import CompletedOrderDetail from './CompletedOrderDetail';

interface OrderDetail {
  status: string;
  status__code: string;
  // Add other fields as needed
}

// Define order status enum
enum OrderStatus {
  UNVERIFIED = 'unverified_order',
  VERIFIED = 'verified_order',
  ARRIVED = 'arrived_order',
  COMPLETED = 'completed_order',
  ORDER_DUE_FOR_RETURN = 'order_due_for_returned',
  ORDER_PENDING_RETURN = 'order_pending_returned',
  OVERDUE_ORDER = 'overdue_order',
  RETURNED_ORDER = 'returned_order',
  PROCESSED_ORDER = 'processed_order',
  CANCELLED = 'cancelled',
  RECEIPT_CANCELLED = 'receipt_cancelled',
}

export default function OrderDetail() {
  const { t } = useTranslation();
  const { id: operationId } = useParams();
  const [searchParams] = useSearchParams();
  const [orderDetail, setOrderDetail] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const orderId = searchParams.get('orderId');

  const fetchOrderDetail = async (orderId: string) => {
    const { data } = await API.get(endpoint.detailOrder(orderId));
    return data;
  };

  useEffect(() => {
    if (orderId) {
      setLoading(true);
      fetchOrderDetail(orderId).then((res) => {
        console.log('res', res);
        setOrderDetail(res);
        setLoading(false);
      });
    }
  }, [orderId]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!orderDetail) return null;

  return (
    <>
      {orderDetail?.id && (
        <CompletedOrderDetail
          data={orderDetail}
          operationId={Number(operationId)}
        />
      )}
    </>
  );
}
