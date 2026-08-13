import { Box, CircularProgress } from '@mui/material';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useSearchParams } from 'react-router-dom';
import { useTheme } from 'rj-core';

import API, { endpoint } from '@/services/API';

import CancelledOrderDetail from './MainTabs/CancelledTab/components/CancelledOrderDetail';
import CompletedOrderDetail from './MainTabs/CompletedTab/components/CompletedOrderDetail';
import ReturnedOrderDetail from './MainTabs/ReturnedTab/components/ReturnedOrderDetail';
import VerificationOrderDetail from './MainTabs/VerificationTab/components/VerificationOrderDetail';
import { ThemeType } from './types';

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

// Map status to components
const ORDER_DETAIL_COMPONENTS = {
  // Add other components as needed
  [OrderStatus.UNVERIFIED]: VerificationOrderDetail,
  [OrderStatus.VERIFIED]: VerificationOrderDetail,
  [OrderStatus.ARRIVED]: CompletedOrderDetail,
  [OrderStatus.COMPLETED]: CompletedOrderDetail,
  [OrderStatus.CANCELLED]: CancelledOrderDetail,
  [OrderStatus.ORDER_DUE_FOR_RETURN]: ReturnedOrderDetail,
  [OrderStatus.ORDER_PENDING_RETURN]: ReturnedOrderDetail,
  [OrderStatus.OVERDUE_ORDER]: ReturnedOrderDetail,
  [OrderStatus.RETURNED_ORDER]: ReturnedOrderDetail,
  [OrderStatus.PROCESSED_ORDER]: ReturnedOrderDetail,
  [OrderStatus.RECEIPT_CANCELLED]: CancelledOrderDetail,
} as const;

export default function OrderDetail() {
  const { t } = useTranslation();
  const { id: operationId } = useParams();
  const [searchParams] = useSearchParams();
  const [orderDetail, setOrderDetail] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [theme] = useTheme() as [ThemeType, (theme: ThemeType) => void];
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

  const DetailComponent =
    ORDER_DETAIL_COMPONENTS[orderDetail?.mapped_status_code as OrderStatus];

  console.log(
    'DetailComponent',
    orderDetail?.mapped_status_code,
    DetailComponent,
  );
  if (!DetailComponent) {
    return null;
  }

  return (
    <>
      {orderDetail?.id && (
        <DetailComponent
          data={orderDetail}
          operationId={Number(operationId)}
        />
      )}
    </>
  );
}
