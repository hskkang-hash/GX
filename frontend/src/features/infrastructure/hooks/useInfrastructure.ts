import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';

const useInfrastructure = () => {
  const { showLoading, hideLoading } = useLoadingContext();

  const getInfrastructureList = async ({
    pageSize = 25,
    currentPage = 1,
    objSearch = {},
  }: {
    pageSize?: number;
    currentPage?: number;
    objSearch?: any;
  }) => {
    const params = {
      page_size: pageSize,
      current_page: currentPage,
      depth: 2,
    };
    if (objSearch) {
      if (objSearch?.searchParams) {
        objSearch?.searchParams.forEach((item: any) => {
          {
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
    showLoading();
    const { success, message, data, total_items, total_pages } = await API.get(
      endpoint.infrastructure,
      { params },
    );
    if (success) {
      hideLoading();
    } else {
      hideLoading();
    }
    return {
      success,
      message,
      data,
      total_items,
      total_pages,
    };
  };

  const getDetailInfrastructure = async (id: number) => {
    showLoading();
    const { success, message, data } = await API.get(
      endpoint.detailInfrastructure(id),
    );
    if (success) {
      hideLoading();
    } else {
      hideLoading();
    }
    return {
      success,
      message,
      data: {
        ...data,
        terminal_purpose_id: {
          value: data?.terminal_purpose__id,
          label: data?.terminal_purpose__name,
        },
        infrastructure_type_id: {
          value: data?.infrastructure_type__id,
          label: data?.infrastructure_type__name,
        },
        purpose_type_id: {
          value: data?.purpose_type__id,
          label: data?.purpose_type__name,
        },
        avatar: data?.avatar__file_url,
      },
    };
  };

  const createInfrastructure = async (data) => {
    try {
      showLoading();
      const imageFile = data?.avatar;

      const clonedFormData = JSON.parse(JSON.stringify(data));

      if (imageFile instanceof File) {
        clonedFormData.avatar = imageFile;
      }
      const config = {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      };
      const formData = new FormData();

      if (clonedFormData.avatar) {
        formData.append('avatar', clonedFormData.avatar);
      }

      formData.append('data', JSON.stringify(clonedFormData));
      const res = await API.post(endpoint.infrastructure, formData, config);
      return {
        success: res.success,
        message: res.message,
      };
    } catch (error) {
      return {
        success: false,
        message: error?.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const updateInfrastructure = async (data, id: number) => {
    try {
      const imageFile = data?.avatar;

      const clonedFormData = JSON.parse(JSON.stringify(data));

      if (imageFile instanceof File) {
        clonedFormData.avatar = imageFile;
      }
      const config = {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      };
      const formData = new FormData();
      if (clonedFormData.avatar) {
        formData.append('avatar', clonedFormData.avatar);
      }
      formData.append('data', JSON.stringify(clonedFormData));
      const { success, message } = await API.put(
        endpoint.detailInfrastructure(id),
        formData,
        config,
      );
      if (success) {
        hideLoading();
      } else {
        hideLoading();
      }
      return {
        success,
        message,
      };
    } catch (error) {
      return {
        success: false,
        message: error?.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const changeStatusInfrastructure = async ({
    ids,
    useLoading = false,
  }: {
    ids: string;
    useLoading?: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const { success, message } = await API.put(
        endpoint.changeStatusInfrastructure(ids),
      );

      return {
        success,
        message,
      };
    } catch (error) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      useLoading && hideLoading();
    }
  };

  const activeInfrastructureAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.activeInfrastructure(ids));
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

  const deactiveInfrastructureAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.deactiveInfrastructure(ids));
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
    getInfrastructureList,
    getDetailInfrastructure,
    createInfrastructure,
    updateInfrastructure,
    changeStatusInfrastructure,

    activeInfrastructureAPI,
    deactiveInfrastructureAPI,
  };
};

export default useInfrastructure;
