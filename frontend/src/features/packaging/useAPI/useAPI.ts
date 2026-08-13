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
  const getPackagingSpecifications = async ({
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
      const response = await API.get(endpoint.packagingSpecifications, {
        params,
      });
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

  const activeDeactivePackaging = async ({
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
      const response = await API.put(endpoint.activeDeactivePackaging(ids));
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

  const createPackaging = async (data: any) => {
    const config = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const dataDevice = convertPackagingData(data);
    try {
      showLoading();
      const response = await API.post(
        endpoint.packagingSpecifications,
        dataDevice,
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
  return {
    getPackagingSpecifications,
    activeDeactivePackaging,
    getDetailPackaging,
    createPackaging,
    updatePackaging,

    activePackagingAPI,
    deactivePackagingAPI,
  };
};

export default useAPI;
