import { useCallback, useState } from 'react';
import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';

import { SearchObject, SearchParam } from '../../../../../types/paramAPI';
import {
  SurveillanceProfileResponse,
  SurveillanceProfileState,
} from '../../../types';

interface SurveillanceProfileCompletedResponse {
  data: SurveillanceProfileState[];
  totalPage: number;
  totalItem: number;
}

export const useCompletedSurveillanceProfiles = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const [surveillanceProfiles, setSurveillanceProfiles] =
    useState<SurveillanceProfileCompletedResponse>({
      data: [],
      totalPage: 0,
      totalItem: 0,
    });

  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [objSearch, setObjSearch] = useState<SearchObject>({});

  const fetchCompletedSurveillanceProfiles = useCallback(async () => {
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
      const response = await API.get(
        endpoint['completedSurveillanceProfiles'],
        { params },
      );

      setSurveillanceProfiles({
        data:
          response?.data?.map((item: SurveillanceProfileResponse) => ({
            id: item.id,
            profile_id: item.id,
            name: item.name,
            purpose__name: item.purpose__name,
            created_on: item.created_on,
            start_time: item.start_time,
            estimated_end_time: item.estimated_end_time,
            actual_start_time: item.actual_start_time,
            actual_end_time: item.actual_end_time,
            total_distance: item.total_distance,
            estimated_time: item.estimated_time,
            mission__log_collection: item.mission__log_collection,
            mission__video_recording: item.mission__video_recording,
            mission__video_analysis: item.mission__video_analysis,
            operator_full_name: item.operator_full_name,
            group__name: item.group__name,
            total_flight_time: item.total_flight_time,
            has_video_analysis: item.has_video_analysis,
          })) || [],
        totalPage: response?.total_pages || 0,
        totalItem: response?.total_items || 0,
      });
    } catch (error) {
      setSurveillanceProfiles({
        data: [],
        totalPage: 0,
        totalItem: 0,
      });
    } finally {
      hideLoading();
    }
  }, [pageSize, currentPage, objSearch, showLoading, hideLoading]);

  return {
    surveillanceProfiles,
    setSurveillanceProfiles,
    pageSize,
    setPageSize,
    currentPage,
    setCurrentPage,
    objSearch,
    setObjSearch,
    fetchCompletedSurveillanceProfiles,
  };
};
