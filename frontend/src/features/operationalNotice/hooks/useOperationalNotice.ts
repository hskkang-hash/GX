import { useTranslation } from 'react-i18next';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../services/API';
import { SearchObject, SearchParam } from '../../../types/paramAPI';
import {
  OperationalNoticeFormValues,
  OperationalNoticeState,
} from '../types/operationalNotice.types';

const useOperationalNotice = () => {
  const { t } = useTranslation();
  const { showLoading, hideLoading } = useLoadingContext();

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

  const getOperationalNotice = async ({
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

      const response = await API.get(endpoint['operationalNotice'], { params });
      console.log('response_2345672334567', response);

      return {
        success: true,
        data: {
          data: response.data.map((item: OperationalNoticeState) => ({
            id: item.id,
            name: item.name,
            active: item.active,
            created_on: item.created_on,
            content1: item.content1,
            content2: item.content2,
            content3: item.content3,
            group__name: item.group__name,
            group__id: item.group__id,
            // notShowCheckbox: item.active > 0,
          })),
          totalPage: response.total_pages || 0,
          totalItem: response.total_items || 0,
        },
      };
    } catch (error) {
      return {
        success: false,
        data: {
          data: [],
          totalPage: 0,
          totalItem: 0,
        },
      };
    } finally {
      hideLoading();
    }
  };

  const getOperationalNoticeDetail = async (id: string) => {
    try {
      showLoading();
      const response = await API.get(
        endpoint.operationalNoticeDetail(Number(id)),
      );
      if (response.success) {
        return {
          data: response?.data || null,
        };
      }
      return {
        data: null,
      };
    } catch (error) {
      return { data: null };
    } finally {
      hideLoading();
    }
  };

  const createOperationalNotice = async (data: OperationalNoticeFormValues) => {
    try {
      showLoading();
      const response = await API.post(endpoint['operationalNotice'], data);
      if (response.success) {
        return {
          data: response?.data || null,
          message: response?.message || null,
          success: true,
        };
      }
      return {
        data: null,
        message: response?.message || null,
        success: false,
      };
    } catch (error) {
      return {
        data: null,
        message:
          (error as { response: { data: { message: string } } })?.response?.data
            ?.message || t('Unexpected error'),
        success: false,
      };
    } finally {
      hideLoading();
    }
  };

  const updateOperationalNotice = async (
    id: number,
    data: OperationalNoticeState,
  ) => {
    try {
      showLoading();
      const response = await API.put(
        endpoint.operationalNoticeDetail(id),
        data,
      );
      if (response.success) {
        return {
          data: response?.data || null,
          message: response?.message || null,
          success: true,
        };
      }
      return {
        data: null,
        message: response?.message || null,
        success: false,
      };
    } catch (error) {
      return {
        data: null,
        message:
          (error as { response: { data: { message: string } } })?.response?.data
            ?.message || t('Unexpected error'),
        success: false,
      };
    } finally {
      hideLoading();
    }
  };

  const changeStatusOperationalNotice = async (id: number) => {
    try {
      showLoading();
      const response = await API.post(
        endpoint.changeStatusOperationalNotice(id),
      );
      if (response.success) {
        return {
          data: response?.data || null,
          message: response?.message || null,
          success: true,
        };
      }
      return {
        data: null,
        message: response?.message || null,
        success: false,
      };
    } catch (error) {
      return error;
    } finally {
      hideLoading();
    }
  };

  const deleteOperationalNotice = async (ids: string) => {
    try {
      showLoading();
      const response = await API.delete(endpoint.deleteOperationalNotice(ids));
      if (response.success) {
        return {
          data: response?.data || null,
          message: response?.message || null,
          success: true,
        };
      }
      return {
        data: null,
        message: response?.message || null,
        success: false,
      };
    } catch (error) {
      return {
        data: null,
        message:
          (error as { response: { data: { message: string } } })?.response?.data
            ?.message || t('Unexpected error'),
        success: false,
      };
    } finally {
      hideLoading();
    }
  };

  return {
    getOperationalNotice,
    getOperationalNoticeDetail,
    getFieldsTemplate,
    createOperationalNotice,
    updateOperationalNotice,
    changeStatusOperationalNotice,
    deleteOperationalNotice,
  };
};

export default useOperationalNotice;
