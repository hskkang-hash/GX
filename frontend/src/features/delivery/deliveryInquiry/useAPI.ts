import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { useLoadingContext } from 'rj-core';

import { convertOrderData } from '@/utils/addNewOrderDataConvert';

import API, { endpoint } from '../../../services/API';
import { DeliveryInquiryState } from './types/DeliveryInquiry.types';

interface DeviceParams {
  page_size: number;
  current_page: number;
  depth: number;
  created_on_start?: string;
  created_on_end?: string;
  main_type__name?: string;
  [key: string]: any;
}
const useAPI = () => {
  const { t } = useTranslation();
  const { showLoading, hideLoading } = useLoadingContext();
  const logFormData = (formData: FormData) => {
    const entries = formData.entries();
    const result: Record<string, any> = {};
    for (const [key, value] of entries) {
      if (key === 'data') {
        result[key] = JSON.parse(value as string);
      } else {
        result[key] = value;
      }
    }
  };

  const getTerminals = ({
    key = 'name',
    value = 'id',
    address,
    pickup_location_id,
  }: { key?: string; value?: string; address?: string; pickup_location_id?: int } = {}) => {
    return async (
      search: string,
      loadedOptions: readonly any[],
      { page }: { page: number } = { page: 1 },
    ) => {
      try {
        const response = await API.get(endpoint.terminalsForOrder, {
          params: {
            current_page: page,
            page_size: 10,
            name: search,
            address: address,
            pickup_location_id: pickup_location_id,
          },
        });
        const data = response.data || [];
        const hasMore = data.length === 10;
        return {
          options: data.map((item: any) => {
            return {
              label: item.full_address,
              value: item.id,
              name: item.name,
              full_address: item.full_address,
            };
          }),
          hasMore,
          additional: {
            page: page + 1,
          },
        };
      } catch (error) {
        console.error('Failed to fetch drones:', error);
        return {
          options: [],
          hasMore: false,
          additional: {
            page: page,
          },
        };
      }
    };
  };

  const getItemType = ({
    key = 'name',
    value = 'id',
  }: { key?: string; value?: string } = {}) => {
    return async (
      search: string,
      loadedOptions: readonly any[],
      { page }: { page: number } = { page: 1 },
    ) => {
      try {
        const response = await API.get(endpoint.itemType, {
          params: {
            page_number: page,
            page_size: 10,
            name: search,
          },
        });
        const data = response.data || [];
        const hasMore = data.length === 10;
        return {
          options: data.map((item: any) => {
            return {
              label: item.name,
              value: item.id,
            };
          }),
          hasMore,
          additional: {
            page: page + 1,
          },
        };
      } catch (error) {
        console.error('Failed to fetch drones:', error);
        return {
          options: [],
          hasMore: false,
          additional: {
            page: page,
          },
        };
      }
    };
  };

  const getDeliveryOption = async () => {
    try {
      const response = await API.get(endpoint.deliveryOption);
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
    }
  };

  const getPackageList = ({
    weight,
    dimension_l,
    dimension_w,
    dimension_h,
    is_waterproof,
    is_fragile,
  }: {
    weight?: number;
    dimension_l?: number;
    dimension_w?: number;
    dimension_h?: number;
    is_waterproof?: boolean;
    is_fragile?: boolean;
  } = {}) => {
    return async (
      search: string,
      loadedOptions: readonly any[],
      { page }: { page: number } = { page: 1 },
    ) => {
      try {
        const response = await API.get(endpoint.packageList, {
          params: {
            page_number: page,
            page_size: 10,
            name: search,
            weight: weight,
            dimension_l: dimension_l,
            dimension_w: dimension_w,
            dimension_h: dimension_h,
            is_waterproof: is_waterproof,
            is_fragile: is_fragile,
          },
        });
        const data = response.data || [];
        const hasMore = data.length === 10;
        return {
          options: data.map((item: any) => {
            return {
              label: item.details,
              value: item.id,
            };
          }),
          hasMore,
          additional: {
            page: page + 1,
          },
        };
      } catch (error) {
        console.error('Failed to fetch drones:', error);
        return {
          options: [],
          hasMore: false,
          additional: {
            page: page,
          },
        };
      }
    };
  };

  const createNewOrder = async (data: any) => {
    const dataOrder = convertOrderData(data);
    try {
      showLoading();
      const response = await API.post(endpoint.deliveryInquiryOrder, dataOrder);
      return {
        success: response.success,
        message: response.message,
        data: response.data,
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

  const getListOrderDetail = async ({
    pageSize = null,
    currentPage = 1,
    objSearch = {},
  }: {
    pageSize?: number | null;
    currentPage?: number;
    objSearch?: any;
  }) => {
    const params: DeviceParams = {
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

      if (objSearch?.mapped_status) {
        params['mapped_status'] = objSearch.mapped_status;
      }
      if (objSearch?.receipt_code) {
        params['receipt_code'] = objSearch.receipt_code;
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
      const response = await API.get(endpoint.deliveryInquiryOrder, { params });
      return {
        success: true,
        data: {
          allow_order_in_bad_weather: response.allow_order_in_bad_weather,
          data: response.data.map((item: DeliveryInquiryState) => item),
          totalItem: response.total_items,
          totalPage: response.total_pages,
        },
        dashboard_auto_refresh: response.dashboard_auto_refresh,
        dashboard_refresh_interval: response.dashboard_refresh_interval,
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
        dashboard_auto_refresh: false,
        dashboard_refresh_interval: 0,
      };
    } finally {
      hideLoading();
    }
  };

  const getDetailOrder = async (id: number) => {
    try {
      showLoading();
      const response = await API.get(endpoint.detailOrder(id));
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

  const getPackageByName = async (name: string) => {
    try {
      const response = await API.get(endpoint.packageList, {
        params: {
          name: name,
        },
      });

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message ||
          'Error getting drone by unique id',
        data: {
          data: [],
        },
      };
    }
  };

  const cancelOrder = async (id: number, reason: string) => {
    try {
      showLoading();
      const response = await API.post(endpoint.cancelOrder(id), {
        reason,
      });
      return {
        success: response.success,
        message: response.message,
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

  const getBanks = () => {
    return async (
      search: string,
      loadedOptions: readonly any[],
      { page }: { page: number } = { page: 1 },
    ) => {
      try {
        const response = await API.get(endpoint.bank, {
          params: {
            page_number: page,
            page_size: 10,
            name: search,
          },
        });
        const data = response.data || [];
        const hasMore = data.length === 10;
        return {
          options: data.map((item: any) => {
            return {
              label: item.name,
              value: item.code,
            };
          }),
          hasMore,
          additional: {
            page: page + 1,
          },
        };
      } catch (error) {
        console.error('Failed to fetch banks:', error);
        return {
          options: [],
          hasMore: false,
          additional: {
            page: page,
          },
        };
      }
    };
  };

  const refundCash = async (id: number, data: any) => {
    try {
      showLoading();
      const response = await API.post(endpoint.refundCash(id), data);
      return {
        success: response.success,
        message: response.message,
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

  const getOrderStatus = async () => {
    try {
      const response = await API.get(endpoint.getOrderStatus);
      return {
        success: true,
        data: response.data.map((item: string) => ({
          label: item,
          value: item,
        })),
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message ||
          'An unknown error occurred',
        data: [],
      };
    }
  };

  const changeOrderStatus = async (id: number) => {
    try {
      const response = await API.post(endpoint.changeOrderStatus(id));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message || t('Unexpected error'),
      };
    }
  };

  return {
    getListOrderDetail,
    getDetailOrder,
    createNewOrder,
    getTerminals,
    getDeliveryOption,
    getItemType,
    getPackageList,
    getPackageByName,
    cancelOrder,
    getBanks,
    refundCash,

    getOrderStatus,
    changeOrderStatus,
  };
};

export default useAPI;
