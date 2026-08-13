import { useCallback, useEffect, useRef, useState } from 'react';
import { ToastTopHelper, useConfigSystem } from 'rj-core';

import { useAutoRefresh } from '@/features/Dashboard/DeliveryDashboard/componentsV2/autoRefresh';

import { useDeliveryInquiryStore } from '../store/deliveryInquiryStore';
import useAPI from '../useAPI';

export const useDeliveryInquiryData = () => {
  const [configSystem] = useConfigSystem();
  const { getListOrderDetail } = useAPI();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const getListOrderDetailRef = useRef(getListOrderDetail);
  const [objSearch, setObjSearch] = useState(null);

  const { data, currentPage, pageSize, setData, setCurrentPage, setPageSize } =
    useDeliveryInquiryStore();

  useEffect(() => {
    getListOrderDetailRef.current = getListOrderDetail;
  }, [getListOrderDetail]);

  const refreshTime =
    configSystem?.['Delivery inquiry refresh']
      ?.delivery_inquiry_refresh_interval || 0;
  const refreshFlag =
    configSystem?.['Delivery inquiry refresh']?.delivery_inquiry_auto_refresh ||
    false;

  const { shouldRefresh, consumeRefreshFlag, resetAutoRefreshTimer } =
    useAutoRefresh({
      refreshTime: refreshTime,
      isActive: refreshFlag ? true : false,
    });

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const fetchData = useCallback(async (): Promise<void> => {
    try {
      const {
        success,
        data: responseData,
        message,
      } = await getListOrderDetailRef.current({
        pageSize: pageSize,
        currentPage: currentPage,
        objSearch: objSearch,
      });

      if (success) {
        setData(responseData);
        return;
      }

      ToastTopHelper.error(message);
    } finally {
      resetAutoRefreshTimer();
    }
  }, [pageSize, currentPage, objSearch, resetAutoRefreshTimer, setData]);

  // Silent fetch without loading indicator for auto-refresh
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const fetchDataSilently = useCallback(async (): Promise<void> => {
    try {
      const { success, data: responseData } =
        await getListOrderDetailRef.current({
          pageSize: pageSize,
          currentPage: currentPage,
          objSearch: objSearch,
        });

      if (success) {
        setData(responseData);
      }
    } finally {
      resetAutoRefreshTimer();
    }
  }, [pageSize, currentPage, objSearch, resetAutoRefreshTimer, setData]);

  useEffect(() => {
    if (shouldRefresh) {
      fetchDataSilently();
      consumeRefreshFlag();
    }
  }, [shouldRefresh, fetchDataSilently, consumeRefreshFlag]);

  useEffect(() => {
    if (pageSize) {
      fetchData();
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [pageSize, currentPage, objSearch, fetchData]);

  return {
    data,
    currentPage,
    pageSize,
    objSearch,
    setCurrentPage,
    setPageSize,
    setObjSearch,
    fetchData,
  };
};
