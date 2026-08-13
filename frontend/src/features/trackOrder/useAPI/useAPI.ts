import dayjs from 'dayjs';
import qs from 'qs';
import { useLoadingContext } from 'rj-core';

import { SearchObject } from '@/types/paramAPI';

import API, { endpoint } from '../../../services/API';
import { formatDateTime } from '../../Handover/utils/dateFormat';

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

  const getDeviceManagement = async ({
    pageSize = 25,
    currentPage = 1,
    objSearch = {},
  }: {
    pageSize?: number;
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
      const response = await API.get(endpoint.deviceManagement, { params });
      return {
        success: true,
        data: {
          data: response.data.map((item: any) => ({
            ...item,
          })),
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

  const deActiveDevice = async ({
    ids,
  }: {
    ids?: string;
  }): Promise<{ success: boolean; message: any }> => {
    if (!ids) {
      return {
        success: false,
        message: 'ID is required',
      };
    }
    try {
      showLoading();
      const response = await API.put(endpoint.activeDeactiveDevice(ids));
      if (response.success) {
        return {
          success: true,
          message: response.message,
        };
      }
      return {
        success: false,
        message: response.message ?? 'Operation failed',
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message ?? 'Unexpected error',
      };
    } finally {
      hideLoading();
    }
  };

  const getDetailOrder = async ({
    id,
    edit,
  }: {
    id: number;
    edit: boolean;
  }) => {
    try {
      const response = await API.get(endpoint.detailEtriOrder(id));
      console.log('response_getDetailOrder', response);
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

  const getListDeviceTemplate = ({
    key = 'name',
    value = 'id',
  }: { key?: string; value?: string } = {}) => {
    return async (
      search: string,
      loadedOptions: any[],
      { page }: { page: number } = { page: 1 },
    ) => {
      try {
        const response = await API.get(endpoint.library, {
          params: {
            current_page: page,
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
  const getDataDeviceTemplateById = async (deviceId: number) => {
    try {
      const response = await API.get(endpoint.libraryDetail(deviceId), {
        params: {
          id: deviceId,
          edit: true,
          depth: 2,
        },
      });
      // const drone = response?.data?.drones?.[0];
      return {
        success: true,
        data: response?.data,
        message: 'Success',
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

  // Track Order
  const fetchTrackOperationOrder = async ({
    pageSize,
    currentPage,
    objSearch,
    // status_codes,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject;
  }) => {
    // const activeSearch = objSearch?.mapped_status;
    // const activeDateSearch = objSearch?.startDate || objSearch?.endDate;

    try {
      showLoading();
      const params: Record<string, any> = {
        page_size: pageSize,
        current_page: currentPage,
      };

      if (objSearch?.startDate) {
        params['created_on_start'] = formatDateTime(
          objSearch.startDate,
          'YYYY-MM-DD',
          'HH:mm:ss',
        );
      }
      if (objSearch?.endDate) {
        params['created_on_end'] = formatDateTime(
          objSearch.endDate,
          'YYYY-MM-DD',
          'HH:mm:ss',
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
      if (objSearch?.mapped_status) {
        params['mapped_status'] = objSearch.mapped_status;
      }
      if (objSearch?.filters) {
        params['filters'] = objSearch.filters;
      }
      if (objSearch?.sortParams && objSearch?.sortParams.length) {
        params.sort_obj = objSearch.sortParams;
      }

      const response = await API.get(endpoint.etriTracking, {
        params: params,
        paramsSerializer: (params) =>
          qs.stringify(params, { arrayFormat: 'repeat' }),
      });

      return {
        success: true,
        data: {
          data: response.data,
          totalItem: response.total_items,
          totalPage: response.total_pages,
        },
      };
    } catch (error: any) {
      return {
        success: false,
        // message: error.response.,
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

  const sendingReceptionInfo = async ({
    operation_id,
  }: {
    operation_id: number;
  }) => {
    try {
      showLoading();
      const response = await API.post(endpoint.sendToEtri(operation_id));

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

  return {
    getDeviceManagement,
    deActiveDevice,
    getDetailOrder,
    sendingReceptionInfo,
    getListDeviceTemplate,
    getDataDeviceTemplateById,
    fetchTrackOperationOrder,
    cancelOrder,
  };
};

export default useAPI;
