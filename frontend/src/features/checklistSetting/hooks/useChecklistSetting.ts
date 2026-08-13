import { useTranslation } from 'react-i18next';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../services/API';
import { SearchObject, SearchParam } from '../../../types/paramAPI';
import { DroneSensorStatusType } from '../../delivery/DeliveryOperation/MainTabs/ProcessingTab/components/DroneSensorStatus';
import {
  ChecklistSettingFormValues,
  ChecklistSettingState,
} from '../types/checklistSetting.types';

const useChecklistSetting = () => {
  const { t } = useTranslation();
  const { showLoading, hideLoading } = useLoadingContext();

  const getChecklistSetting = async ({
    currentPage,
    pageSize,
    objSearch,
  }: {
    currentPage: number;
    pageSize: number;
    objSearch?: SearchObject;
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
      const response = await API.get(endpoint['checklistSetting'], { params });
      console.log("response_34343434", response)
      return {
        data: response.data.map((item: ChecklistSettingState) => ({
          id: item.id,
          item_name: item.item_name,
          created_on: item.created_on,
          category__name: item.category_name,
          category_id: item.category_id,
          item_name_translations: item.item_name_translations,
          group__name: item.group__name,
          group__id: item.group__id,
          is_active: item.is_active,
        })),
        auto_checklist:
          response?.auto_checklist?.sensorStatus?.automaticCheckItems.map(
            (item: DroneSensorStatusType) => ({
              name: item.name,
              situation: item.situation,
              status: item.status,
              present: item.present,
              health: item.health,
              enabled: item.enabled,
            }),
          ),
        auto_checklist_drone_status: response?.auto_checklist?.drone_status || '',
        sensorStatus: response?.auto_checklist?.sensorStatus?.systemStatus?.system || {},
        totalPage: response.total_pages || 0,
        totalItem: response.total_items || 0,
      };
    } catch (error) {
      return { data: [], totalPage: 0, totalItem: 0 };
    } finally {
      hideLoading();
    }
  };

  const createChecklistSetting = async (data: ChecklistSettingFormValues) => {
    try {
      showLoading();
      const response = await API.post(endpoint['checklistSetting'], data);
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

  const updateChecklistSetting = async (
    id: number,
    data: ChecklistSettingFormValues,
  ) => {
    try {
      showLoading();
      const response = await API.put(
        endpoint['checklistSetting'] + `${id}`,
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

  const deleteChecklistSetting = async (ids: string) => {
    try {
      showLoading();
      const response = await API.delete(
        endpoint['deleteChecklistSetting'](ids),
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

  const getSettingCategory = async () => {
    try {
      const response = await API.get(endpoint['settingCategory']);
      return response.data;
    } catch (error) {
      return [];
    }
  };

  return {
    getChecklistSetting,
    createChecklistSetting,
    updateChecklistSetting,
    deleteChecklistSetting,
    getSettingCategory,
  };
};

export default useChecklistSetting;
