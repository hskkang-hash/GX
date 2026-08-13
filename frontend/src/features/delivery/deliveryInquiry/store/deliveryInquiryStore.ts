import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import {
  DeliveryInquiryData,
  DeliveryInquiryPageState,
} from '../types/DeliveryInquiry.types';

const initialState = {
  data: {
    data: [],
    totalItem: 0,
    totalPage: 0,
  },
  currentPage: 1,
  pageSize: null,
};

export const useDeliveryInquiryStore = create<DeliveryInquiryPageState>()(
  persist(
    (set) => ({
      // persist data
      pageSize: initialState.pageSize,
      currentPage: initialState.currentPage,
      setPageSize: (pageSize: number) => set({ pageSize }),
      setCurrentPage: (currentPage: number) => set({ currentPage }),

      // non-persist
      data: initialState.data,
      setData: (data: DeliveryInquiryData) => set({ data }),
      resetStore: () => set(initialState),
    }),
    {
      name: 'delivery-inquiry-store',
      // persist data pageSize
      partialize: (state) => ({
        pageSize: state.pageSize,
        currentPage: state.currentPage,
      }),
    },
  ),
);
