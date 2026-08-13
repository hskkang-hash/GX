import qs from 'qs';
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';

interface SearchParam {
  id: string;
  value: string | number | boolean;
}

// Define interface for sort params
interface SortParam {
  id: string;
  desc: boolean;
}

// Define interface for the search object
interface SearchObject {
  searchParams?: SearchParam[];
  filters?: Record<string, unknown>;
  sortParams?: SortParam[];
  status_codes?: string | string[];
}

interface CompletedOrder {
  order_id: string;
  order_time: string;
  sender: string;
  recipient: string;
  creator: string;
  number_of_package: number;
}

interface CompletedOrdersResponse {
  data: CompletedOrder[];
  totalItem: number;
  totalPage: number;
}

export const useCompletedOrders = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const { i18n } = useTranslation();

  const fetchArrivedOrders = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject;
  }) => {
    try {
      showLoading();
      const paramsFetch: {
        page_size: number;
        current_page: number;
        filters?: Record<string, unknown>;
        sort_obj?: SortParam[];
        [key: string]: unknown;
      } = {
        page_size: pageSize,
        current_page: currentPage,
      };

      if (objSearch) {
        if (objSearch?.searchParams) {
          objSearch?.searchParams.forEach((item: SearchParam) => {
            paramsFetch[item.id] = item.value;
          });
        }
        if (objSearch?.filters) {
          paramsFetch['filters'] = objSearch.filters;
        }
        if (objSearch?.sortParams && objSearch?.sortParams.length) {
          paramsFetch.sort_obj = objSearch.sortParams;
        }
      }

      const response = await API.get(endpoint.arrivedOrder, {
        params: paramsFetch,
      });

      return {
        data: response.data,
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch (err) {
      console.log(err);
    } finally {
      hideLoading();
    }
  };

  const fetchCompletedOrders = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject;
  }) => {
    try {
      showLoading();
      const paramsFetch: {
        page_size: number;
        current_page: number;
        filters?: Record<string, unknown>;
        sort_obj?: SortParam[];
        [key: string]: unknown;
      } = {
        page_size: pageSize,
        current_page: currentPage,
      };

      if (objSearch) {
        if (objSearch?.searchParams) {
          objSearch?.searchParams.forEach((item: SearchParam) => {
            paramsFetch[item.id] = item.value;
          });
        }
        if (objSearch?.filters) {
          paramsFetch['filters'] = objSearch.filters;
        }
        if (objSearch?.sortParams && objSearch?.sortParams.length) {
          paramsFetch.sort_obj = objSearch.sortParams;
        }
      }

      const response = await API.get(endpoint.completedOrder, {
        params: paramsFetch,
      });

      return {
        data: response.data,
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch (err) {
      console.log(err);
    } finally {
      hideLoading();
    }
  };

  const fetchOperationOrder = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject;
  }) => {
    try {
      showLoading();
      const paramsFetch: Record<string, any> = {
        page_size: pageSize,
        current_page: currentPage,
      };

      if (objSearch) {
        if (objSearch.status_codes) {
          paramsFetch.status_codes = objSearch.status_codes;
        }

        if (objSearch.searchParams) {
          objSearch.searchParams.forEach((item: SearchParam) => {
            paramsFetch[item.id] = item.value;
          });
        }

        if (objSearch.filters) {
          paramsFetch.filters = objSearch.filters;
        }

        if (objSearch.sortParams?.length) {
          paramsFetch.sort_obj = objSearch.sortParams;
        }
      }

      const response = await API.get(endpoint.operationOrder, {
        params: paramsFetch,
        paramsSerializer: (params: any) =>
          qs.stringify(params, { arrayFormat: 'repeat' }),
      });

      return {
        data: response.data,
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch (err) {
      console.log(err);
    } finally {
      hideLoading();
    }
  };

  const fetchDeliveryReport = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject;
  }) => {
    try {
      showLoading();
      const paramsFetch: Record<string, any> = {
        page_size: pageSize,
        current_page: currentPage,
      };

      if (objSearch) {
        // Don't send status_codes - API automatically filters for completed_order
        if (objSearch.searchParams) {
          objSearch.searchParams.forEach((item: SearchParam) => {
            paramsFetch[item.id] = item.value;
          });
        }

        if (objSearch.filters) {
          paramsFetch.filters = objSearch.filters;
        }

        if (objSearch.sortParams?.length) {
          paramsFetch.sort_obj = objSearch.sortParams;
        }
      }

      const response = await API.get(endpoint.deliveryReport, {
        params: paramsFetch,
        paramsSerializer: (params: any) =>
          qs.stringify(params, { arrayFormat: 'repeat' }),
      });

      return {
        data: response.data,
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch (err) {
      console.log(err);
    } finally {
      hideLoading();
    }
  };

  return {
    fetchArrivedOrders,
    fetchCompletedOrders,
    fetchOperationOrder,
    fetchDeliveryReport,
  };
};
