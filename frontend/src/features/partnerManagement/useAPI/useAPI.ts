import dayjs from 'dayjs';
import { useLoadingContext } from 'rj-core';

import { convertPackagingData } from '@/utils/packingDataConverter';

import API, { endpoint } from '../../../services/API';

interface PackagingParams {
  page_size: number;
  current_page: number;
  depth: number;
  created_on_start?: string;
  created_on_end?: string;
  main_type__name?: string;
  [key: string]: any;
}
const useAPI = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const getPartnerManagement = async ({
    pageSize = 25,
    currentPage = 1,
    objSearch = {},
  }: {
    pageSize?: number;
    currentPage?: number;
    objSearch?: any;
  }) => {
    const params: PackagingParams = {
      page_size: pageSize,
      current_page: currentPage,
      depth: 2,
    };
    if (objSearch) {
      if (objSearch?.startDate) {
        params['created_on_start'] = dayjs(objSearch.startDate).format(
          'YYYY-MM-DD HH:mm:ss',
        );
      }
      if (objSearch?.endDate) {
        params['created_on_end'] = dayjs(objSearch.endDate).format(
          'YYYY-MM-DD HH:mm:ss',
        );
      }
      if (objSearch?.searchParams) {
        objSearch?.searchParams.forEach((item: any) => {
          if (item.id === 'main_type') {
            params['main_type__name'] = item.value;
          } else {
            params[item.id] = item.value;
          }
        });
      }
      if (objSearch?.filters) {
        params['filters'] = objSearch.filters;
      }
      if (objSearch?.sortParams && objSearch?.sortParams.length) {
        params.sort_obj = objSearch.sortParams;
      }
    }
    try {
      showLoading();
      const response = await API.get(endpoint.partner, {
        params,
      });

      console.log('response_get_partner', response);
      return {
        success: true,
        data: {
          data:
            response.data.map((item: any) => ({
              api_callback_url: {
                DroneUserNotice: item.api_callback_url?.DroneUserNotice || '-',
                DroneBaseStation:
                  item.api_callback_url?.DroneBaseStation || '-',
                DeliveryStatusCallback:
                  item.api_callback_url?.DeliveryStatusCallback || '-',
              },
              service_key: item?.service || '-',
              refresh: item.refresh || '',
              group_id: item.group_id || '-',
              group__name: item.group__name || '-',
              id: item.id || '-',
              name: item.name || '-',
              created_on: item.created_on || '-',
              code: item.code || '-',
              api_user: item.api_user || '-',
              remaining_days: item.remaining_days || '0',
              is_active: item.is_active,
              in_use: item.in_use,
              expired_days: item.expired_days || '0',
              expired: item.expired,
              notShowCheckbox: item.in_use > 0,
            })) || [],
          totalItem: response.total_items,
          totalPage: response.total_pages,
        },
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
        data: {
          data: [],
          totalItem: 0,
          totalPage: 0,
        },
      };
    } finally {
      hideLoading();
    }
  };

  const deletePartner = async ({
    ids,
  }: {
    ids?: string;
  }): Promise<{ success: boolean; message: any }> => {
    try {
      showLoading();
      const response = await API.delete(endpoint.deletePartner(ids as string));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const getDetailPackaging = async ({
    id,
    edit,
  }: {
    id: number;
    edit: boolean;
  }) => {
    try {
      showLoading();
      const response = await API.get(endpoint.detailPackaging(id, edit));

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message ||
          'An unknown error occurred',
        data: {
          data: [],
        },
      };
    } finally {
      hideLoading();
    }
  };

  const copyTokenPartner = async ({ id }: { id: number }) => {
    try {
      showLoading();
      const response = await API.get(endpoint.copyTokenPartner(id));
      return {
        success: response.success,
        message: 'API Key copied',
        data: response.data,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
        data: null,
      };
    } finally {
      hideLoading();
    }
  };

  const createPartner = async (data: any) => {
    // const config = {
    //   headers: {
    //     'Content-Type': 'application/json',
    //   },
    // };

    // const dataDevice = convertPackagingData(data);
    try {
      showLoading();
      const response = await API.post(endpoint.partner, data);
      console.log('response_create_partner', response);
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };
  const updatePartner = async ({ id, data }: { id: number; data: any }) => {
    try {
      showLoading();
      const response = await API.put(endpoint.updatePartner(id), data);
      console.log('response_update_partner', response);
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const updatePackaging = async (data: any) => {
    const config = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    try {
      showLoading();
      const response = await API.put(
        endpoint.detailPackaging(data.id, false),
        data.data,
        config,
      );
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const activePackagingAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.activePackaging(ids));
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

  const deactivePackagingAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.deactivePackaging(ids));
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

  const refreshTokenPartner = async ({
    id,
    refresh_token,
  }: {
    id: number;
    refresh_token: string;
  }) => {
    try {
      showLoading();
      const response = await API.post(endpoint.refreshTokenPartner(id), {
        ...(refresh_token ? { refresh_token } : {}),
      });
      console.log('response_refresh_token_partner', response);
      return {
        success: response.success,
        message: response.message,
        data: response.data,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
        data: null,
      };
    } finally {
      hideLoading();
    }
  };

  return {
    getPartnerManagement,
    deletePartner,
    getDetailPackaging,
    createPartner,
    updatePackaging,
    refreshTokenPartner,
    deactivePackagingAPI,
    updatePartner,
    copyTokenPartner,
  };
};

export default useAPI;
