import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';

const useDockingStation = () => {
  const { showLoading, hideLoading } = useLoadingContext();

  const getDockingStationList = async ({
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
      endpoint.dockingStation,
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

  const getDetailDockingStation = async (id: number) => {
    showLoading();
    const { success, message, data } = await API.get(
      endpoint.detailDockingStation(id),
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
        docking_station_type_id: {
          value: data?.docking_station_type__id,
          label: data?.docking_station_type__name,
        },
        time_stops: {
          value: data?.time_stops?.value || null,
          unit: data?.time_stops?.unit || 'mins',
        },
        avatar: data?.avatar__file_url,
      },
    };
  };

  const createDockingStation = async (data) => {
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
      const res = await API.post(endpoint.dockingStation, formData, config);
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

  const updateDockingStation = async (data, id: number) => {
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
      const res = await API.put(
        endpoint.detailDockingStation(id),
        formData,
        config,
      );
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

  const changeStatusDockingStation = async ({
    ids,
    useLoading = false,
  }: {
    ids: string;
    useLoading?: boolean;
  }) => {
    useLoading && showLoading();
    try {
      const { success, message } = await API.put(
        endpoint.changeStatusDockingStation(ids),
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

  const activeDockingStationAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.activeDockingStation(ids));
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

  const deactiveDockingStationAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.deactiveDockingStation(ids));
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
    getDockingStationList,
    getDetailDockingStation,
    createDockingStation,
    updateDockingStation,
    changeStatusDockingStation,

    activeDockingStationAPI,
    deactiveDockingStationAPI,
  };
};

export default useDockingStation;
