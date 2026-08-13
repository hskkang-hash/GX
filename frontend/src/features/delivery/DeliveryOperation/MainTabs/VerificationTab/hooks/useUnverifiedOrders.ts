import { useState, useEffect } from 'react';
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
}

interface UnverifiedOrder {
  order_id: string;
  order_time: string;
  sender: string;
  recipient: string;
  creator: string;
  number_of_package: number;
}

interface UnverifiedOrdersResponse {
  data: UnverifiedOrder[];
  totalItem: number;
  totalPage: number;
}

export const useUnverifiedOrders = () => {
  const { showLoading, hideLoading } = useLoadingContext();

  const fetchUnverifiedOrders = async ({
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

      const response = await API.get(endpoint.unVerifiedOrder, {
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

  const fetchVerifiedOrders = async ({
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

      const response = await API.get(endpoint.verifiedOrder, {
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

  return {
    fetchUnverifiedOrders,
    fetchVerifiedOrders,
  };
};
