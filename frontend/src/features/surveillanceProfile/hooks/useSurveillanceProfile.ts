import dayjs, { Dayjs } from 'dayjs';
import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ToastTopHelper, useLoadingContext, useUserInfo } from 'rj-core';
import { v4 as uuidv4 } from 'uuid';

import API, { endpoint } from '@/services/API';
import {
  addListDownloadFile,
  addTaskIdToFile,
  removeFile,
} from '@/utils/actionFileManagement';

import { Waypoint } from '../../SurveyMission/types/surveyMission.types';
import { useDrawingModeStore } from '../stores/drawingModeStore';
import { DroneAssignment, SurveillanceProfileResponse } from '../types';
import { extractWaypoints } from '../utils/convertMarkerData';

interface ChartDataItem {
  waypointName: string;
  cruise_speed: number;
  operating_altitude: number;
  cumulativeDistance: number;
  order: number;
}

interface ChartDataPoint {
  name: string;
  cruise_speed: number;
  operating_altitude: number;
  distance: number;
  order: number;
}

interface MarkerPoint {
  lat: number;
  lng: number;
  name?: string;
  color?: string;
  operating_altitude?: number;
  routeId?: string | number;
}
// Define interface for search params
interface SearchParam {
  id: string;
  value: string | number | boolean;
}

// Define interface for sort params
interface SortParam {
  id: string;
  desc: boolean;
}

// Define interface for the search object
interface SearchObject {
  searchParams?: SearchParam[];
  filters?: Record<string, unknown>;
  sortParams?: SortParam[];
}
interface droneChanged {
  assignment_id: number;
  device_code: string;
  device_name: string;
  device_unit_id: string;
  from_device_id: number;
  model: string;
  profile_id: number;
  to_device_id: number;
}

export const useSurveillanceProfile = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const { t } = useTranslation();

  const userInfo = useUserInfo() as { profile__group__name?: string } | null;
  const userGroup = userInfo?.profile__group__name || '';

  const currentUserId = useMemo(() => {
    if (!userInfo) return undefined;
    return (
      (userInfo as { user_id?: number | string })?.user_id ||
      (userInfo as { id?: number | string })?.id ||
      undefined
    );
  }, [userInfo]);

  const [detailSurveillanceProfile, setDetailSurveillanceProfile] =
    useState<SurveillanceProfileResponse | null>(null);

  const [markerData, setMarkerData] = useState<MarkerPoint[]>([]);
  console.log('detailSurveillanceProfile3423434', detailSurveillanceProfile);
  console.log('markerData3423434', markerData);

  const setCurrentShape = useDrawingModeStore((state) => state.setCurrentShape);
  const clearAll = useDrawingModeStore((state) => state.clearAll);

  const getListMissionOptions = () => {
    return async (
      search: string,
      _loadedOptions: unknown,
      { page }: { page: number },
    ) => {
      const response = await API.get(endpoint.surveyMission, {
        params: {
          name: search,
          current_page: page ?? 1,
          page_size: 10,
          is_active: true,
        },
      });
      const data: Array<{
        id?: number;
        name?: string;
        drone_segments?: unknown[];
        from_route?: boolean;
      }> = response.data || [];
      const hasMore = response.current_page < response.total_pages;
      const options = data
        .map((item) => {
          if (item.id === undefined || !item.name) {
            return null;
          }
          return {
            label: item.name,
            value: item.id,
            from_gcs:
              (Array.isArray(item?.drone_segments) &&
                item?.drone_segments?.length > 0) ||
              item?.from_route,
          };
        })
        .filter(
          (option): option is { label: string; value: number } =>
            option !== null,
        );

      return {
        options,
        hasMore,
        additional: {
          page: (page ?? 1) + 1,
        },
      };
    };
  };

  const getListOperatorOptions = () => {
    return async (
      search: string,
      _loadedOptions: unknown,
      { page }: { page: number },
    ) => {
      const response = await API.get(endpoint.surveyOperator, {
        params: {
          full_name: search,
          current_page: page ?? 1,
          page_size: 10,
          group__name: userGroup,
        },
      });

      const data: Array<{ id?: number; full_name?: string }> =
        response.data || [];
      const hasMore = response.current_page < response.total_pages;
      const options = data
        .map((item) => {
          if (item.id === undefined || !item.full_name) {
            return null;
          }
          return { label: item.full_name, value: item.id };
        })
        .filter(
          (option): option is { label: string; value: number } =>
            option !== null,
        );

      return {
        options,
        hasMore,
        additional: {
          page: (page ?? 1) + 1,
        },
      };
    };
  };

  const fetchListAvalableDrones = async ({
    mission_id,
    start_time,
  }: {
    mission_id: number | null;
    start_time: string | null;
  }) => {
    try {
      showLoading();
      const response = await API.get(endpoint.listAvalableDrones, {
        params: {
          mission_id: mission_id,
          start_time: start_time,
        },
      });

      const statusCode =
        (response as { status_code?: number })?.status_code ??
        (response as { statusCode?: number })?.statusCode;
      const isOk =
        (response as { success?: boolean })?.success === true &&
        (statusCode === undefined || statusCode === 200); 

      if (!isOk) {
        return {
          success: false,
          data: [],
          status_code: statusCode ?? 400,
          message:
            (response as { message?: string })?.message || 'Something went wrong',
        };
      }

      return {
        success: true,
        data: response.data,
        status_code: statusCode ?? 200,
        message: (response as { message?: string })?.message,
      };
    } catch (error) {
      console.error('Error fetching list avalable drones:', error);
      const errorResponse = error as {
        response?: {
          status?: number;
          data?: {
            status_code?: number;
            message?: string;
            detail?: string;
          };
        };
        status?: number;
        status_code?: number;
        message?: string;
      };
      const statusCode =
        errorResponse.response?.data?.status_code ??
        errorResponse.response?.status ??
        errorResponse.status_code ??
        errorResponse.status ??
        400;
      const message =
        errorResponse.response?.data?.message ||
        errorResponse.response?.data?.detail ||
        errorResponse.message ||
        'Something went wrong';
      return {
        success: false,
        data: [],
        status_code: statusCode,
        message,
      };
    } finally {
      hideLoading();
    }
  };

  const fetchChangeDroneOptions = async ({
    profile_id,
    start_waypoint_id,
    end_waypoint_id,
    objSearch,
    pageSize,
    currentPage,
  }: {
    profile_id: number;
    start_waypoint_id: number;
    end_waypoint_id: number;
    objSearch: SearchObject;
    pageSize: number;
    currentPage: number;
  }) => {
    try {
      showLoading();
      const paramsFetch: {
        profile_id: number;
        start_waypoint_id: number;
        end_waypoint_id: number;
        page_size: number;
        current_page: number;
        filters?: Record<string, unknown>;
        sort_obj?: SortParam[];
        [key: string]: unknown;
      } = {
        page_size: pageSize,
        current_page: currentPage,
        profile_id: profile_id,
        start_waypoint_id: start_waypoint_id,
        end_waypoint_id: end_waypoint_id,
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

      const response = await API.get(endpoint.changeDroneOptions(profile_id), {
        params: paramsFetch,
      });

      return {
        success: true,
        data: {
          data: response.data?.items,
          totalPage: response.total_pages,
          totalItem: response.total_items,
        },
      };
    } catch (error) {
      console.error('Error fetching change drone options:', error);
      const errorResponse = error as {
        response?: { data?: { message?: string } };
      };
      return {
        success: false,
        data: {
          data: [],
          totalPage: 0,
          totalItem: 0,
        },
        message: errorResponse.response?.data?.message,
      };
    } finally {
      hideLoading();
    }
  };

  const fetchChangeDroneProfile = async ({
    profile_id,
    from_drone_id,
    to_drone_id,
  }: {
    profile_id: number;
    from_drone_id: number;
    to_drone_id: number;
  }) => {
    try {
      showLoading();

      const response = await API.post(endpoint.changeDroneProfile(profile_id), {
        from_drone_id: from_drone_id,
        to_drone_id: to_drone_id,
      });
      return {
        success: true,
        data: response.data ?? ({} as droneChanged),
        message: response.message,
      };
    } catch (error) {
      console.error('Error changing drone profile:', error);
      const errorResponse = error as {
        response?: { data?: { message?: string } };
      };
      return {
        success: false,
        data: {},
        message:
          errorResponse.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const createSurveillanceProfileAPI = async (data: {
    name: string;
    mission_id: number;
    start_time: string | null;
    operator_id: number;
    repeat_type_id: number;
    repeat_until_type_id?: number;
    repeat_until_date?: string | null;
    repeat_occurrences?: number | null;
    color_code: string;
    note: string;
    drones: DroneAssignment[];
  }) => {
    try {
      showLoading();
      const response = await API.post(endpoint.addSurveillanceProfile, data);
      return {
        success: true,
        message: response.message,
      };
    } catch (error) {
      const errorResponse = error as {
        response?: { data?: { message?: string } };
      };
      const message =
        errorResponse.response?.data?.message || 'Something went wrong';

      return {
        success: false,
        message,
      };
    } finally {
      hideLoading();
    }
  };

  const fetchDetailSurveillanceProfile = useCallback(
    async (id: number) => {
      try {
        showLoading();
        // Reset previous data immediately to prevent stale content showing
        // while loading new data (fixes modal showing old content on re-open)
        setDetailSurveillanceProfile(null);
        setMarkerData([]);
        clearAll();
        const response = await API.get(
          endpoint['detailSurveillanceProfile'](id),
        );

        if (response.success) {
          const processedChartData = response.data.chart_data
            .sort((a: ChartDataPoint, b: ChartDataPoint) => a.order - b.order)
            .map(
              (
                item: ChartDataPoint,
                index: number,
                array: ChartDataPoint[],
              ): ChartDataItem => {
                // Calculate cumulative distance up to this waypoint
                const cumulativeDistance = array
                  .slice(0, index + 1)
                  .reduce((sum, waypoint) => sum + (waypoint.distance || 0), 0);

                return {
                  waypointName: item.name,
                  cruise_speed: item.cruise_speed || 0,
                  operating_altitude: item.operating_altitude || 0,
                  cumulativeDistance:
                    Math.round(cumulativeDistance * 100) / 100, // Round to 2 decimal places
                  order: item.order,
                };
              },
            );

          const isLineMission = response.data?.mission__line_mission || false;

          const markerDataLine = extractWaypoints(
            response.data?.drone_assignments,
          );

          setMarkerData(markerDataLine);

          const points = isLineMission
            ? response.data?.mission__all_waypoints?.map(
                (waypoint: Waypoint) => ({
                  lat: Number(waypoint.latitude),
                  lng: Number(waypoint.longitude),
                }),
              )
            : response.data?.mission__polygon?.map(
                (point: [number, number]) => ({
                  lat: point[0],
                  lng: point[1],
                }),
              ) || [];

          const newShape = {
            id: uuidv4(),
            type: (isLineMission
              ? 'LINE'
              : response.data?.mission__polygon?.length === 16
                ? 'CIRCULAR'
                : response.data?.mission__polygon?.length === 4
                  ? 'POLYGON'
                  : 'TRACE') as 'LINE' | 'CIRCULAR' | 'POLYGON' | 'TRACE',
            points,
            pointsLength: isLineMission ? points.length : null,
            return: response.data?.mission__return_to_home || false,
          };

          setCurrentShape(newShape);

          setDetailSurveillanceProfile({
            id: response.data.id,
            name: response.data.name,
            region: response.data.mission__region ?? response.data.region ?? null,
            mission: response.data.mission,
            mission_id: response.data.mission__id,
            start_time: response.data.start_time,
            actual_start_time: response.data.actual_start_time,
            end_time: response.data.estimated_end_time,
            repeat: response.data.repeat_type,
            repeat_type__code: response.data.repeat_type__code,
            repeat_type_id: response.data.repeat_type_id,
            repeat_until_type_id: response.data.repeat_until_type_id,
            repeat_until_type__name: response.data.repeat_until_type__name,
            repeat_occurrences: response.data.repeat_occurrences,
            repeat_until_date: response.data.repeat_until_date,
            repeat_type__name: response.data.repeat_type__name,
            repeat_until_type__code: response.data.repeat_until_type__code,
            operator: response.data.operator_full_name,
            operator__id: response.data.operator__id,
            operator__first_name: response.data.operator__first_name,
            purpose: response.data.purpose__name,
            return: response.data.mission__return_to_home,
            maximum_number_of_drones: response.data.mission__maximum_drones,
            total_distance: response.data.total_distance,
            total_estimated_time: response.data.estimated_time,
            note: response.data.note,
            chart_data: processedChartData,
            status__code: response.data.status__code,
            rejection_reason: response.data.metadata
              ? response.data.metadata.rejection_note
              : null,
            devices: response.data.devices,
            color_code: response.data.color_code,
            cancel_reason: response.data.cancel_reason,
            altitude: response?.data?.altitude ?? '150 m',
            takeoff_altitude: response?.data?.takeoff_altitude ?? '100 m',
            altitude_separation: response?.data?.altitude_separation ?? '10 m',
            drone_assignments:
              response.data.drone_assignments?.map(
                (assignment: {
                  id: number;
                  device__id: number;
                  device__serial_number: string;
                  scheduled_start_time: string;
                  start_waypoint__name: string;
                  end_waypoint__name: string;
                  log_collection: boolean;
                  log_path: string;
                  video_recording: boolean;
                  video_analysis: boolean;
                  device__color: string;
                  video_path: string;
                  route_path: {
                    latitude: number;
                    longitude: number;
                    name?: string;
                  }[];
                  analysis_path: string;
                  start_waypoint_id: number;
                  end_waypoint_id: number;
                  device__name: string;
                  waiting_coordinates: [number, number];
                }) => ({
                  id: assignment.id,
                  device__id: assignment.device__id,
                  drone: assignment.device__serial_number,
                  start_time: assignment.scheduled_start_time,
                  start_point: assignment.start_waypoint__name,
                  end_point: assignment.end_waypoint__name,
                  log: assignment.log_collection,
                  log_path: assignment.log_path || '',
                  record: assignment.video_recording,
                  analysis: assignment.video_analysis,
                  video_path: assignment.video_path || '',
                  analysis_path: assignment.analysis_path || '',
                  color: assignment.device__color,
                  route_path: assignment.route_path,
                  start_waypoint_id: assignment.start_waypoint_id,
                  end_waypoint_id: assignment.end_waypoint_id,
                  device__library: assignment.device__library,
                  device__name: assignment.device__name,
                  waiting_coordinates: assignment.waiting_coordinates,
                }),
              ) || [],
            has_video_analysis: response.data.has_video_analysis,
          });
        }
      } catch (error) {
        setDetailSurveillanceProfile(null);
      } finally {
        hideLoading();
      }
    },
    [
      showLoading,
      hideLoading,
      setDetailSurveillanceProfile,
      setCurrentShape,
      setMarkerData,
      clearAll,
    ],
  );

  const getListSurveillanceProfileAPI = async ({
    pageSize,
    currentPage,
    objSearch,
    active,
    status__code,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject;
    active?: boolean;
    status__code?: string;
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

      if (typeof active !== 'undefined') {
        paramsFetch.active = active;
      }

      if (status__code) {
        paramsFetch.status__code = status__code;
      }

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

      const response = await API.get(endpoint.listSurveillanceProfile, {
        params: paramsFetch,
      });

      return {
        data: {
          data: response.data?.items,
          totalPage: response.total_pages,
          totalItem: response.total_items,
        },
        message: response.message,
        success: true,
      };
    } catch (error) {
      console.error('Error fetching surveillance profiles:', error);
      return {
        data: {
          data: [],
          totalPage: 0,
          totalItem: 0,
        },
        message: 'Error fetching surveillance profiles',
        success: false,
      };
    } finally {
      hideLoading();
    }
  };

  const getSurveillanceProfileOptionsAPI = () => {
    return async (
      filterdate: { start_time: string; end_time: string },
      search: string,
      loadedOptions: any,
      { page }: { page: number },
    ) => {
      const response = await API.get(endpoint.listOptionsProfile, {
        params: {
          ...(search ? { name: search } : {}),
          current_page: page ?? 1,
          page_size: 1000,
          start_time_start: filterdate.start_time,
          start_time_end: filterdate.end_time,
        },
      });
      const data = response.data || [];
      // const hasMore = response.current_page < response.total_pages;
      return {
        options: data
          .map((item: any) => {
            return { label: item.name, value: item.id };
          })
          .filter(Boolean),
        // hasMore,
        additional: {
          page: (page ?? 1) + 1,
        },
      };
    };
  };

  const approveSurveillanceProfileAPI = async (id: number) => {
    try {
      showLoading();
      const response = await API.post(
        endpoint['approveSurveillanceProfile'](id),
      );
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const rejectSurveillanceProfileAPI = async (
    profile_id: number,
    reason: string,
  ) => {
    try {
      showLoading();
      const response = await API.post(
        endpoint['rejectSurveillanceProfile'](profile_id),
        { reason: reason },
      );
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };
  const cancelSurveillanceProfileAPI = async (
    profile_id: number,
    reason: string,
  ) => {
    try {
      showLoading();
      const response = await API.post(
        endpoint['cancelSurveillanceProfile'](profile_id),
        { reason: reason },
      );
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const getEventsSurveillanceProfileAPI = async (
    selectedProfilesIds?: string,
    selectedDate: string,
  ) => {
    try {
      showLoading();
      const response = await API.get(endpoint.profilesTimeline, {
        params: {
          ...(selectedProfilesIds ? { profile_ids: selectedProfilesIds } : {}),
          created_on: selectedDate,
        },
      });
      return {
        data: response.data,
        message: response.message,
        success: response.success,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error?.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const fetchDroneStatus = async ({ drone_uuid }: { drone_uuid: string }) => {
    const response = await API.get(endpoint.droneStatus, {
      params: {
        unique_id: drone_uuid,
      },
    });
    if (response?.success) {
      return {
        success: true,
        data: {
          ...response?.data?.active_drone,
        },
      };
    } else {
      return {
        success: false,
        data: null,
      };
    }
  };

  const stopRepeatProfile = async ({ profile_id }: { profile_id: number }) => {
    try {
      showLoading();
      const response = await API.post(endpoint.stopRepeatProfile(profile_id));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      console.error('Error stopping repeat profile', error);
      return {
        success: false,
        message: error.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const cancelProfile = async ({
    profile_id,
    reason,
  }: {
    profile_id: number;
    reason: string;
  }) => {
    try {
      showLoading();
      const response = await API.post(endpoint.cancelProfile(profile_id), {
        reason: reason,
      });
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      console.error('Error canceling profile', error);
      return {
        success: false,
        message: error.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const downloadLogProfile = async ({ profile_id }: { profile_id: number }) => {
    try {
      showLoading();
      const response = await API.get(endpoint.downloadLogProfile(profile_id), {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `log_${profile_id}.json`;
      a.click();
      window.URL.revokeObjectURL(url);
      ToastTopHelper.success(t('Log profile downloaded successfully'));
    } catch (error: any) {
      ToastTopHelper.error(
        error.response?.data?.message || t('Something went wrong'),
      );
    } finally {
      hideLoading();
    }
  };

  const downloadAnalysisProfile = async ({
    profile_id,
  }: {
    profile_id: number;
  }) => {
    try {
      showLoading();
      const response = await API.get(
        endpoint.downloadAnalysisProfile(profile_id),
        {
          responseType: 'blob',
        },
      );
      const url = window.URL.createObjectURL(new Blob([response]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis_${profile_id}.json`;
      a.click();
      window.URL.revokeObjectURL(url);
      ToastTopHelper.success(t('Analysis profile downloaded successfully'));
    } catch (error: any) {
      console.error('Error downloading analysis profile', error);
      ToastTopHelper.error(
        error.response?.data?.message || t('Something went wrong'),
      );
    } finally {
      hideLoading();
    }
  };

  const downloadReportProfile = async ({
    profile_id,
  }: {
    profile_id: number;
  }) => {
    const fileKey = profile_id.toString();
    try {
      const filename = `analysis_profile_${profile_id}_${dayjs().format('YYYY-MM-DD_HH-mm-ss')}.zip`;

      addListDownloadFile({
        id_file: fileKey,
        name: filename,
        type: 'downloadSurveillanceAnalysis',
        userId: currentUserId,
      });

      const response = await API.post(
        endpoint.downloadAnalysisProfileForProfile(profile_id),
      );
      console.log(' API Response:', response);

      const taskId = response?.data?.task_id;
      console.log('Task ID:', taskId);

      if (taskId) {
        addTaskIdToFile(
          taskId,
          fileKey,
          'downloadSurveillanceAnalysis',
          'download',
        );
        console.log(' Task ID added to file');
      } else {
        console.log('No task ID in response');
        removeFile(fileKey, 'downloadSurveillanceAnalysis');
      }

      return {
        success: true,
        message: response?.message || t('Download request queued successfully'),
      };
    } catch (error: any) {
      console.error('Error downloading analysis profile:', error);
      console.error('Error response:', error?.response);
      removeFile(fileKey, 'downloadSurveillanceAnalysis');
      return {
        success: false,
        message: error.response?.data?.message || t('Something went wrong'),
      };
    }
  };

  const actionCheckComplete = async ({
    profile_id,
    drone_checks,
    not_yet,
  }: {
    profile_id: number;
    drone_checks: Array<{
      profile_drone_id: number;
      drone_id: number;
      check_lists: number[];
      auto_checklist: any[];
    }>;
    not_yet?: boolean;
  }) => {
    try {
      showLoading();
      const payload: Record<string, any> = {
        drone_checks: drone_checks,
      };
      if (not_yet !== undefined) {
        payload.not_yet = not_yet;
      }
      const response = await API.post(
        endpoint.checkCompleteProfile(profile_id),
        payload,
      );

      if (response.success) {
        const message =
          response?.data?.message?.en || response?.data?.message?.kr
            ? response?.data?.message?.en || response?.data?.message?.kr
            : response.message;
        return {
          success: true,
          message: message,
        };
      } else {
        return {
          success: false,
          message: response.message,
        };
      }
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  return {
    approveSurveillanceProfileAPI,
    rejectSurveillanceProfileAPI,
    cancelSurveillanceProfileAPI,
    getListMissionOptions,
    getListOperatorOptions,
    fetchListAvalableDrones,
    fetchDetailSurveillanceProfile,
    detailSurveillanceProfile,
    setDetailSurveillanceProfile,
    markerData,
    createSurveillanceProfileAPI,
    getListSurveillanceProfileAPI,
    getSurveillanceProfileOptionsAPI,
    getEventsSurveillanceProfileAPI,
    fetchDroneStatus,
    stopRepeatProfile,
    cancelProfile,
    downloadLogProfile,
    downloadAnalysisProfile,
    downloadReportProfile,
    fetchChangeDroneOptions,
    fetchChangeDroneProfile,
    actionCheckComplete,
  };
};
