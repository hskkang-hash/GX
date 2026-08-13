import { useTranslation } from 'react-i18next';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../services/API';
import { SearchObject, SearchParam } from '../../../types/paramAPI';
import {
  MappingStatusFormValues,
  MappingStatusResponse,
} from '../types/mappingStatus.types';

const useMappingStatus = () => {
  const { t } = useTranslation();
  const { showLoading, hideLoading } = useLoadingContext();

  const getListMappingStatus = async ({
    currentPage,
    pageSize,
    objSearch,
    groupId,
  }: {
    currentPage: number | null;
    pageSize: number | null;
    objSearch: SearchObject;
    groupId?: number;
  }) => {
    try {
      showLoading();
      const params: {
        page_size: number | null;
        current_page: number | null;
        sort_obj?: Array<{ id: string; desc: boolean }>;
        filters?: Record<string, unknown>;
        [key: string]: unknown;
      } = {
        page_size: pageSize,
        current_page: currentPage,
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
      if (groupId) {
        params.group_id = groupId;
      }
      const response = await API.get(endpoint['mappingStatus'], { params });
      return groupId
        ? response.data.map((item: MappingStatusResponse) => ({
            status_guardianx: {
              id: item.delivery_status__id,
              name: item.delivery_status__name,
            },
            status_anyang: item.external_order_statuses_ids,
          }))
        : {
            data: response.data.map((item: MappingStatusResponse) => ({
              id: item.id,
              name: item.name,
              created_on: item.created_on,
              group__name: item.group__name,
              group__id: item.group__id,
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

  const createMappingStatus = async (data: MappingStatusFormValues) => {
    try {
      showLoading();
      const response = await API.post(endpoint['mappingStatus'], data);
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

  const updateMappingStatus = async (
    group_id: number,
    data: MappingStatusFormValues,
  ) => {
    try {
      showLoading();
      const response = await API.put(
        endpoint['updateMappingStatus'](group_id),
        data,
      );
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

  const deleteMappingStatus = async (ids: string) => {
    try {
      showLoading();
      const response = await API.delete(endpoint['deleteMappingStatus'](ids));
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

  const getOrderStatusOptions = async ({ id }: { id: number }) => {
    try {
      const response = await API.get(endpoint['orderStatus'], {
        params: {
          group_id: id,
        },
      });

      if (response.success) {
        return response.data.map((item: { id: number; name: string }) => ({
          value: item.id,
          label: item.name,
        }));
      }
      return [];
    } catch (error) {
      return [];
    }
  };

  const getStatusDelivery = async () => {
    try {
      const response = await API.get(endpoint.getDataForSelectInput, {
        params: {
          model_name: 'deliverystatus',
          multi_language: true,
          page_size: 10000,
        },
      });
      return response.data.map((item: { id: number; name: string }) => ({
        id: item.id,
        name: item.name,
      }));
    } catch (error) {
      return [];
    }
  };

  return {
    getListMappingStatus,
    createMappingStatus,
    updateMappingStatus,
    deleteMappingStatus,
    getOrderStatusOptions,
    getStatusDelivery,
  };
};

export default useMappingStatus;
