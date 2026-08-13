import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';
import { SearchObject, SearchParam } from '@/types/paramAPI';

import { WaybillTemplateData, WaybillTemplateFormValues } from '../type';

const useWaybill = () => {
  const { showLoading, hideLoading } = useLoadingContext();

  const getWaybillTemplateList = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch: SearchObject;
  }) => {
    try {
      showLoading();
      const params: {
        page_size: number;
        current_page: number;
        sort_obj?: Array<{ id: string; desc: boolean }>;
        filters?: Record<string, unknown>;
        [key: string]: unknown;
      } = {
        page_size: pageSize,
        current_page: currentPage ? currentPage : 1,
      };

      if (objSearch) {
        if (objSearch?.searchParams) {
          objSearch?.searchParams.forEach((item: SearchParam) => {
            params[item.id] = item.value;
          });
        }
        if (objSearch?.filters) {
          params['filters'] = objSearch.filters;
        }
        if (objSearch?.sortParams && objSearch?.sortParams.length) {
          params.sort_obj = objSearch.sortParams;
        }
      }

      const response = await API.get(endpoint.waybillTemplate, { params });
      return {
        data:
          response.data?.map((item: WaybillTemplateData) => ({
            id: item.id,
            name: item.name,
            template: item.template,
            group__name: item.group__name,
            group__id: item.group__id,
            created_on: item.created_on,
            is_enabled: item.is_enabled,
            is_default: item.is_default,
            usage_count: item.usage_count || '0',
            notShowCheckbox: item.is_default,
          })) || [],
        totalPage: response.total_pages || 0,
        totalItem: response.total_items || 0,
      };
    } catch {
      return { data: [], totalPage: 0, totalItem: 0 };
    } finally {
      hideLoading();
    }
  };

  const getFieldsTemplate = async (model_name = 'order') => {
    try {
      const response = await API.get(endpoint.getFieldsTemplate, {
        params: { model_name },
      });
      return response;
    } catch {
      return [];
    }
  };

  const getWaybillTemplate = async (id: string) => {
    try {
      const response = await API.get(endpoint.actionWaybillTemplate + '/' + id);
      return {
        id: response.data?.id || '',
        name: response.data?.name || '',
        group: response.data?.group__id
          ? {
              label: response.data?.group__name,
              value: response.data?.group__id,
            }
          : null,
        template: response.data?.template || '',
        css: response.data?.css || '',
        is_default: response.data?.is_default || false,
        is_enabled: response.data?.is_enabled || false,
      };
    } catch {
      return {
        id: '',
        name: '',
        group: null,
        template: '',
        css: '',
        is_default: false,
        is_enabled: true,
      };
    }
  };
  const addNewWaybillTemplate = async (data: WaybillTemplateFormValues) => {
    try {
      const response = await API.post(endpoint.actionWaybillTemplate, data);

      if (response.success) {
        return {
          success: true,
          message: response.message,
        };
      }
      return {
        success: false,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    }
  };

  const updateWaybillTemplate = async (
    id: number,
    data: WaybillTemplateFormValues,
  ) => {
    try {
      const response = await API.put(
        endpoint.actionWaybillTemplate + '/' + id,
        data,
      );

      if (response.success) {
        return {
          success: true,
          message: response.message,
        };
      }
      return {
        success: false,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    }
  };

  const deleteWaybillTemplate = async (ids: string) => {
    try {
      const response = await API.delete(
        endpoint.actionWaybillTemplate + '/' + ids,
      );
      if (response.success) {
        return {
          success: true,
          message: response.message,
        };
      }
      return {
        success: false,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    }
  };

  return {
    getWaybillTemplateList,
    getFieldsTemplate,
    addNewWaybillTemplate,
    updateWaybillTemplate,
    deleteWaybillTemplate,
    getWaybillTemplate,
  };
};

export default useWaybill;
