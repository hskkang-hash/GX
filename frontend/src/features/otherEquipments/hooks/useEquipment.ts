import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';

const useEquipment = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const getEquipmentList = async ({
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
      'api/devices/cameras',
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
      totalItem: total_items,
      totalPage: total_pages,
    };
  };

  const getDetailEquipment = async (id: number) => {
    showLoading();
    const { success, message, data } = await API.get(
      endpoint.detailEquipment(id, false),
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
        name: data.name,
        resolution: {
          width: {
            value: data.resolution.width,
            unit: data.resolution.unit,
          },
          height: {
            value: data.resolution.height,
            unit: data.resolution.unit,
          },
        },
        frame_rate: {
          value: data.frame_rate.value,
          unit: data.frame_rate.unit,
        },
        field_of_view: {
          value: [data.field_of_view.min, data.field_of_view.max],
          unit: data.field_of_view.unit,
        },
        weight: {
          min: {
            value: data.weight.min,
            unit: data.weight.original_unit,
          },
          max: {
            value: data.weight.max,
            unit: data.weight.original_unit,
          },
        },
        image_stabilization: {
          value: data.image_stabilization_id,
          label: data.image_stabilization__name,
        },
        note: data.note || '',
        group: data.group__id
          ? {
              value: data.group__id,
              label: data.group__name,
            }
          : null,
      },
    };
  };

  const createEquipment = async (data) => {
    showLoading();
    const { success, message } = await API.post('api/devices/cameras', data);
    if (success) {
      hideLoading();
    } else {
      hideLoading();
    }
    return {
      success,
      message,
    };
  };

  const updateEquipment = async (data, id: number) => {
    showLoading();
    const { success, message } = await API.put(
      `api/devices/cameras/${id}`,
      data,
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
  };

  const changeStatusEquipment = async ({ ids }) => {
    showLoading();
    const { success, message } = await API.put(
      endpoint.changeStatusEquipment(ids),
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
  };

  const activeEquipmentAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.activeEquipment(ids));
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

  const deactiveEquipmentAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.deactiveEquipment(ids));
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
    getEquipmentList,
    getDetailEquipment,
    createEquipment,
    updateEquipment,
    changeStatusEquipment,

    activeEquipmentAPI,
    deactiveEquipmentAPI,
  };
};

export default useEquipment;
