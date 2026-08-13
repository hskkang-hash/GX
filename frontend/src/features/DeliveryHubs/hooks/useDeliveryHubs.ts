import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';
import { SearchObject, SearchParam, SortParam } from '@/types/paramAPI';

import { FormRegisterData } from '../types/IDeliveryHubs';

export const useDeliveryHubs = () => {
  const { showLoading, hideLoading } = useLoadingContext();

  const getDeliveryHubsAPI = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject | null;
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

      const response = await API.get(endpoint.hubs, {
        params: paramsFetch,
      });

      return {
        data: response.data,
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch {
      return { data: [], totalPage: 0, totalItem: 0 };
    } finally {
      hideLoading();
    }
  };

  const getDetailDeliveryHubsAPI = async (id: number) => {
    try {
      showLoading();
      const response = await API.get(endpoint.hubs + `/${id}`);
      if (response.success) {
        return {
          success: true,
          message: response.message,
          data: response.data,
        };
      }
      return {
        success: false,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      hideLoading();
    }
  };

  const createDeliveryHubsAPI = async (data: FormRegisterData) => {
    try {
      showLoading();
      const response = await API.post(endpoint.hubs, data);

      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      hideLoading();
    }
  };

  const updateDeliveryHubsAPI = async ({
    id,
    data,
  }: {
    id: number;
    data: FormRegisterData;
  }) => {
    try {
      showLoading();
      const response = await API.put(endpoint.hubs + `/${id}`, data);
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      hideLoading();
    }
  };

  const activeDeactiveDeliveryHubsAPI = async (
    ids: string,
    useLoading = false,
  ) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.changeStatusHubs(ids));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      useLoading && hideLoading();
    }
  };

  const activeDeliveryHubsAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.activeDeliveryHub(ids));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      useLoading && hideLoading();
    }
  };

  const deactiveDeliveryHubsAPI = async ({
    ids,
    useLoading,
    deactive_reason_id,
  }: {
    ids: string;
    useLoading: boolean;
    deactive_reason_id?: number;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.deactiveDeliveryHub(ids), {
        ...(deactive_reason_id && { deactive_reason_id }),
      });
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      useLoading && hideLoading();
    }
  };

  return {
    getDeliveryHubsAPI,
    getDetailDeliveryHubsAPI,
    createDeliveryHubsAPI,
    updateDeliveryHubsAPI,
    activeDeactiveDeliveryHubsAPI,

    activeDeliveryHubsAPI,
    deactiveDeliveryHubsAPI,
  };
};
