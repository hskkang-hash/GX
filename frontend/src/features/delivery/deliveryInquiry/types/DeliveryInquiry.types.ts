import { SearchParam } from '../../../../types/paramAPI';

interface DeliveryInquiryState {
  order_code: string;
  created_on: string;
  sender_name: string;
  recipient_name: string;
  origin: string;
  destination: string;
  status__name: [];
  reason: string;
  id: number;
}

interface DeliveryInquiryData {
  data: DeliveryInquiryState[];
  totalItem: number;
  totalPage: number;
}

interface DeliveryInquiryPageState {
  // Data
  data: DeliveryInquiryData;
  currentPage: number;
  pageSize?: number | null;
  // Actions
  setData: (data: DeliveryInquiryData) => void;
  setCurrentPage: (page: number) => void;
  setPageSize: (size: number) => void;
  resetStore: () => void;
}

interface PaymentConfigState {
  paymentEnabled: boolean | null;
  setConfig: (enabled: boolean) => void;
  fetchConfig: (id: number) => Promise<void>;
}

export type {
  DeliveryInquiryState,
  DeliveryInquiryData,
  DeliveryInquiryPageState,
  PaymentConfigState,
};
