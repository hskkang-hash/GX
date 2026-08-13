import { useTranslation } from 'react-i18next';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../services/API';
import { SearchObject, SearchParam } from '../../../types/paramAPI';
import {
  OrderStatusFormValues,
  OrderStatusResponse,
} from '../types/orderStatus.types';

const useOrderStatus = () => {
  const { t } = useTranslation();
  const { showLoading, hideLoading } = useLoadingContext();

  const getListOrderStatus = async ({
    currentPage,
    pageSize,
    objSearch,
  }: {
    currentPage: number;
    pageSize: number;
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
      const response = await API.get(endpoint['orderStatus'], { params });
      return {
        data: response.data.map((item: OrderStatusResponse) => ({
          id: item.id,
          name: item.name,
          name_en_translation: item.name_en_translation,
          name_ko_translation: item.name_ko_translation,
          name_th_translation: item.name_th_translation,
          value: item.value,
          created_on: item.created_on,
          text_color: item.text_color,
          background_color: item.background_color,
          border_color: item.border_color,
          group__name: item.group__name,
          group__id: item.group__id,
          no_background_color: item.background_color ? false : true,
          no_border_color: item.border_color ? false : true,
        })),
        totalPage: response.total_pages || 0,
        totalItem: response.total_items || 0,
      };
    } catch (error) {
      return { data: [], totalPage: 0, totalItem: 0 };
    } finally {
      hideLoading();
    }
  };

  const createOrderStatus = async (data: OrderStatusFormValues) => {
    try {
      showLoading();
      const response = await API.post(endpoint['orderStatus'], data);
      return {
        message: response.message,
        success: response.success,
      };
    } catch (error) {
      return {
        message:
          (error as { response: { data: { message: string } } })?.response?.data
            ?.message || t('Unexpected error'),
        success: false,
      };
    } finally {
      hideLoading();
    }
  };

  const updateOrderStatus = async (id: number, data: OrderStatusFormValues) => {
    try {
      showLoading();
      const response = await API.put(endpoint['orderStatus'] + `/${id}`, data);
      return {
        message: response.message,
        success: response.success,
      };
    } catch (error) {
      return {
        message:
          (error as { response: { data: { message: string } } })?.response?.data
            ?.message || t('Unexpected error'),
        success: false,
      };
    } finally {
      hideLoading();
    }
  };

  const deleteOrderStatus = async (ids: string) => {
    try {
      showLoading();
      const response = await API.delete(endpoint['deleteOrderStatus'](ids));
      return {
        message: response.message,
        success: response.success,
      };
    } catch (error) {
      return {
        message:
          (error as { response: { data: { message: string } } })?.response?.data
            ?.message || t('Unexpected error'),
        success: false,
      };
    }
  };

  return {
    getListOrderStatus,
    createOrderStatus,
    updateOrderStatus,
    deleteOrderStatus,
  };
};

export default useOrderStatus;
