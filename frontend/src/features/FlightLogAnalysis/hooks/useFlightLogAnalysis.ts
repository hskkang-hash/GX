import { useTranslation } from 'react-i18next';
import { ToastTopHelper, useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../services/API';
import { SearchObject, SearchParam, SortParam } from '../../../types/paramAPI';
import { FlightLogAnalysisState } from '../types/flightLogAnalysis.types';

export const useFlightLogAnalysis = () => {
  const { t } = useTranslation();
  const { showLoading, hideLoading } = useLoadingContext();

  const getLogAnalysisAPI = async ({
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
      const paramsFetch: {
        page_size: number;
        current_page: number;
        filters?: Record<string, unknown>;
        sort_obj?: SortParam[];
        [key: string]: unknown;
      } = {
        page_size: pageSize,
        current_page: currentPage,
      };

      if (objSearch) {
        if (objSearch?.searchParams) {
          objSearch?.searchParams.forEach((item: SearchParam) => {
            paramsFetch[item.id] = item.value;
          });
        }
        if (objSearch?.filters) {
          paramsFetch['filters'] = objSearch.filters;
        }
        if (objSearch?.sortParams && objSearch?.sortParams.length) {
          paramsFetch.sort_obj = objSearch.sortParams;
        }
      }

      const response = await API.get(endpoint.flightLogAnalysis, {
        params: paramsFetch,
      });
      return {
        data: response.data.map((item: FlightLogAnalysisState) => ({
          id: item.id,
          route_code: item.route_code,
          route_name: item.route_name,
          start_time: item.start_time,
          end_time: item.end_time,
          total_distance: item.total_distance,
          start_point__name: item.start_point__name,
          end_point__name: item.end_point__name,
          drone_anomaly_prediction__name: item.drone_anomaly_prediction__name,
          drone_anomaly_prediction__code: item.drone_anomaly_prediction__code,
          group__name: item.group__name,
          service_name: t(item.service_name),
          drone_name: item.drone_name,
          profile_drone__profile: item.profile_drone__profile,
          mission_id: item.mission_id,
          mission_name: item.mission_name,
        })),
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch {
      return { data: [], totalPage: 0, totalItem: 0 };
    } finally {
      hideLoading();
    }
  };

  const getDetailLogAnalysisAPI = async (id: number) => {
    try {
      showLoading();
      const response = await API.get(endpoint.detailFlightLogAnalysis(id));
      return {
        data: response.data,
      };
    } catch (error) {
      ToastTopHelper.error(
        (error as unknown as { response: { data: { message: string } } })
          ?.response?.data?.message || t('Failed to get detail log analysis'),
      );
      return { data: null };
    } finally {
      hideLoading();
    }
  };

  const downloadFlightLogAnalysisAPI = async (id: number) => {
    try {
      const response = await API.get(endpoint.downloadFlightLogAnalysis(id), {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `flight_log_analysis_${id}.json`;
      a.click();
      window.URL.revokeObjectURL(url);
      ToastTopHelper.success(t('Flight log analysis downloaded successfully'));
    } catch (error) {
      ToastTopHelper.error(
        (error as unknown as { response: { data: { message: string } } })
          ?.response?.data?.message ||
          t('Failed to download flight log analysis'),
      );
    }
  };

  const deleteFlightLogAnalysisAPI = async (ids: string) => {
    try {
      showLoading();
      const response = await API.delete(endpoint.deleteFlightLogAnalysis(ids));
      return { success: response.success, message: response.message };
    } catch (error) {
      ToastTopHelper.error(
        (error as unknown as { response: { data: { message: string } } })
          ?.response?.data?.message ||
          t('Failed to delete flight log analysis'),
      );
      return { success: false, message: null };
    } finally {
      hideLoading();
    }
  };

  return {
    getLogAnalysisAPI,
    getDetailLogAnalysisAPI,
    downloadFlightLogAnalysisAPI,
    deleteFlightLogAnalysisAPI,
  };
};
