import { useTranslation } from 'react-i18next';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../services/API';
import { SearchObject, SearchParam } from '../../../types/paramAPI';
import {
  ReportTemplateFormValues,
  ReportTemplateState,
} from '../types/reportTemplate.types';

const useReportTemplate = () => {
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

  const getReportTemplate = async ({
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

      const response = await API.get(endpoint['reportTemplate'], { params });
      return {
        data: response.data.map((item: ReportTemplateState) => ({
          id: item.id,
          name: item.name,
          is_enabled: item.is_enabled,
          is_default: item.is_default,
          template: item.template,
          usage_count: item.usage_count,
          created_on: item.created_on,
          group__name: item.group__name,
          notShowCheckbox:
            (item.usage_count && item.usage_count > 0) || item.is_default,
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

  const getReportTemplateDetail = async (id: string) => {
    try {
      showLoading();
      const response = await API.get(endpoint['reportTemplate'] + `${id}`);
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

  const createReportTemplate = async (data: ReportTemplateFormValues) => {
    try {
      showLoading();
      const response = await API.post(endpoint['reportTemplate'], data);
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

  const updateReportTemplate = async (
    id: number,
    data: ReportTemplateFormValues,
  ) => {
    try {
      showLoading();
      const response = await API.put(
        endpoint['reportTemplate'] + `${id}`,
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

  const deleteReportTemplate = async (ids: string) => {
    try {
      showLoading();
      const response = await API.delete(endpoint['deleteReportTemplate'](ids));
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
    getReportTemplate,
    getReportTemplateDetail,
    getFieldsTemplate,
    createReportTemplate,
    updateReportTemplate,
    deleteReportTemplate,
  };
};

export default useReportTemplate;
