import dayjs from 'dayjs';
import { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useLoadingContext, useUserInfo } from 'rj-core';

import API, { endpoint } from '../../../services/API';
import { useFileManagementStore } from '../../../store/FileManagement.store';
import { SearchObject, SearchParam } from '../../../types/paramAPI';
import {
  addListDownloadFile,
  addTaskIdToFile,
  updateListDownloadFile,
} from '../../../utils/actionFileManagement';
import {
  ImportMissionFormValues,
  SurveyMissionFormValues,
  SurveyMissionState,
} from '../types/surveyMission.types';

export const useSurveyMission = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const { t } = useTranslation();
  const userInfo = useUserInfo();

  const currentUserId = useMemo(() => {
    if (!userInfo) return undefined;
    return (
      (userInfo as { user_id?: number | string })?.user_id ||
      (userInfo as { id?: number | string })?.id ||
      undefined
    );
  }, [userInfo]);

  const wait = useCallback(
    (ms: number) => new Promise((resolve) => setTimeout(resolve, ms)),
    [],
  );

  const checkPermissionActionSurveyMission = async () => {
    try {
      showLoading();
      const response = await API.get(
        endpoint['checkPermissionActionSurveyMission'],
      );
      return response.data;
    } catch (error) {
      return false;
    } finally {
      hideLoading();
    }
  };

  const getSurveyMission = async ({
    currentPage,
    pageSize,
    objSearch,
  }: {
    currentPage: number;
    pageSize: number;
    objSearch?: SearchObject | null;
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
      const response = await API.get(endpoint['surveyMission'], { params });

      return {
        data:
          response?.data?.map((item: SurveyMissionState) => ({
            id: item.id,
            code: item.code,
            name: item.name,
            status__name: item.status__name,
            status__code: item.status__code,
            is_active: item.is_active,
            created_by_full_name: item.created_by_full_name,
            created_on: item.created_on,
            start_point: item.start_point,
            end_point: item.end_point,
            total_distance: item.total_distance,
            estimated_time: item.estimated_time,
            note: item.note,
            group__name: item.group__name,
            group__id: item.group__id,
            notShowCheckbox: item.status__code !== 'approved',
          })) || [],
        totalPage: response?.total_pages || 0,
        totalItem: response?.total_items || 0,
      };
    } catch (error) {
      return {
        data: [],
        totalPage: 0,
        totalItem: 0,
      };
    } finally {
      hideLoading();
    }
  };

  const getDetailSurveyMission = async ({ id }: { id: number }) => {
    try {
      showLoading();
      const response = await API.get(endpoint['detailSurveyMission'](id));
      return {
        data: response.data,
      };
    } catch (error) {
      return {
        data: null,
      };
    } finally {
      hideLoading();
    }
  };

  const addSurveyMission = async ({
    data,
  }: {
    data: SurveyMissionFormValues;
  }) => {
    try {
      showLoading();
      const response = await API.post(endpoint['surveyMission'], data);
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as unknown as { response?: { data?: { message?: string } } })
            ?.response?.data?.message || t('Something went wrong'),
      };
    } finally {
      hideLoading();
    }
  };

  const updateSurveyMission = async ({
    id,
    data,
  }: {
    id: number;
    data: SurveyMissionFormValues;
  }) => {
    try {
      showLoading();
      const response = await API.put(endpoint['detailSurveyMission'](id), data);
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as unknown as { response?: { data?: { message?: string } } })
            ?.response?.data?.message || t('Something went wrong'),
      };
    } finally {
      hideLoading();
    }
  };

  const reviewSurveyMission = async ({
    data,
  }: {
    data: {
      polygon: [][];
      altitude: number;
      takeoff_altitude: number;
      altitude_separation: number;
      survey_angle: number;
      frontal_overlap: number;
      side_overlap: number;
      entry_location: number;
      cruise_speed: number;
      hover_speed: number;
      spacing: number;
      turnaround_distance: number;
      trigger_distance: number;
    };
  }) => {
    try {
      showLoading();
      const response = await API.post(endpoint['reviewSurveyMission'], data);
      if (response.success) {
        return {
          data: response.data,
        };
      }
    } catch (error) {
      return {
        data: null,
      };
    } finally {
      hideLoading();
    }
  };

  const approveSurveyMission = async ({ id }: { id: number }) => {
    try {
      showLoading();
      const response = await API.post(endpoint['approveSurveyMission'](id));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as unknown as { response?: { data?: { message?: string } } })
            ?.response?.data?.message || t('Something went wrong'),
      };
    } finally {
      hideLoading();
    }
  };

  const rejectSurveyMission = async ({
    id,
    data,
  }: {
    id: number;
    data: {
      reason: string;
    };
  }) => {
    try {
      showLoading();

      const response = await API.post(
        endpoint['rejectSurveyMission'](id),
        data,
      );
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      console.log(error.response?.data?.message);
      return {
        success: false,
        message: error.response?.data?.message || t('Something went wrong'),
      };
    } finally {
      hideLoading();
    }
  };

  const activateSurveyMission = async ({ ids }: { ids: string }) => {
    try {
      showLoading();
      const response = await API.post(endpoint['activateSurveyMission'](ids));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as unknown as { response?: { data?: { message?: string } } })
            ?.response?.data?.message || t('Something went wrong'),
      };
    } finally {
      hideLoading();
    }
  };

  const deactivateSurveyMission = async ({ ids }: { ids: string }) => {
    try {
      showLoading();
      const response = await API.post(endpoint['deactivateSurveyMission'](ids));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as unknown as { response?: { data?: { message?: string } } })
            ?.response?.data?.message || t('Something went wrong'),
      };
    } finally {
      hideLoading();
    }
  };

  const getListRouteForImportMission = ({
    key = 'name',
    value = 'id',
  }: {
    key?: string;
    value?: string;
  }) => {
    return async (
      search: string,
      loadedOptions: any,
      { page = 1, page_size = 10 }: { page?: number; page_size?: number } = {
        page: 1,
        page_size: 10,
      },
    ) => {
      try {
        const paramsFetch: {
          page_size: number;
          current_page: number;
          name: string;
          is_active: string;
        } = {
          current_page: page,
          page_size: page_size,
          name: search,
          is_active: 'True',
        };
        const response = await API.get(endpoint.routes, {
          params: paramsFetch,
        });

        console.log('response', response);
        const data = response?.data || [];
        const hasMore = response.current_page < response.total_pages;
        return {
          options: data.map((item: any) => ({
            label: item.name,
            value: item.id,
          })),
          hasMore,
          additional: {
            page: (page ?? 1) + 1,
          },
        };
      } catch (error) {
        console.error('Failed to fetch drones:', error);
        return {
          options: [],
          hasMore: false,
          additional: {
            page: page,
          },
        };
      }
    };
  };

  const pollTaskStatus = useCallback(
    async ({
      taskId,
      fileKey,
      displayName,
      type,
      onSuccess,
      onError,
    }: {
      taskId?: string;
      fileKey: string;
      displayName: string;
      type:
      | 'downloadFileAll'
      | 'downloadFileDrone'
      | 'downloadFileRobot'
      | 'importMission';
      onSuccess?: () => void;
      onError?: () => void;
    }) => {
      if (!taskId) return;

      // Kiểm tra xem file có thuộc user hiện tại không trước khi poll
      const fileManagementState = useFileManagementStore.getState();
      const fileItem = fileManagementState.downloadFileManagement.find(
        (file) => file.gxId === fileKey && file.gxType === type,
      );

      // Nếu file có userId và không khớp với user hiện tại, không poll
      if (
        fileItem?.userId &&
        currentUserId !== null &&
        fileItem.userId !== currentUserId &&
        String(fileItem.userId) !== String(currentUserId)
      ) {
        console.log(
          `Skipping poll for file ${fileKey} - belongs to different user`,
        );
        return;
      }

      const maxAttempts = 60; // Max attempts to poll the task status
      const intervalMs = 5000; // Interval to poll the task status

      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        // Kiểm tra lại userId trước mỗi lần poll
        const currentFileState = useFileManagementStore.getState();
        const currentFile = currentFileState.downloadFileManagement.find(
          (file) => file.gxId === fileKey && file.gxType === type,
        );

        // Nếu file đã bị xóa hoặc không còn thuộc user hiện tại, dừng poll
        if (!currentFile) {
          console.log(`File ${fileKey} no longer exists, stopping poll`);
          return;
        }

        if (
          currentFile.userId &&
          currentUserId !== null &&
          currentFile.userId !== currentUserId &&
          String(currentFile.userId) !== String(currentUserId)
        ) {
          console.log(
            `File ${fileKey} no longer belongs to current user, stopping poll`,
          );
          return;
        }

        try {
          const response = await API.get(endpoint.checkTaskSocket(taskId));
          const statusData = response?.data as {
            status?: string;
            download_url?: string;
            file_url?: string;
            filename?: string;
            message?: string;
            data?: {
              download_url?: string;
              file_url?: string;
              filename?: string;
            };
          };

          if (statusData?.status) {
            const normalizedStatus = statusData.status.toLowerCase();
            if (
              normalizedStatus === 'success' ||
              normalizedStatus === 'completed'
            ) {
              await updateListDownloadFile({
                id_file: fileKey,
                status: 'done',
                type,
              });

              onSuccess?.();
              return { success: true, message: statusData.message };
            }

            if (normalizedStatus === 'failed' || normalizedStatus === 'error') {
              await updateListDownloadFile({
                id_file: fileKey,
                status: 'error',
                type,
              });

              onError?.();
              return { success: false, message: statusData.message };
            }
          }
        } catch (error) {
          console.error(`Error polling task status ${taskId}:`, error);
        }

        await wait(intervalMs);
      }

      // Timeout - max attempts reached
      await updateListDownloadFile({
        id_file: fileKey,
        status: 'error',
        type,
      });
      onError?.();
      return { success: false, message: t('Import mission timeout') };
    },
    [wait, currentUserId, t],
  );
  const importSurveyMissionAPI = useCallback(
    async (
      data: ImportMissionFormValues,
      options?: {
        onSuccess?: () => void;
        onError?: () => void;
      },
    ) => {
      const fileKey = `${data.name}-${dayjs().format('YYYY-MM-DD-HH-mm-ss')}`;
      const displayName = `${data.name}-${dayjs().format('YYYY-MM-DD-HH-mm-ss')}`;

      try {
        const response = await API.post(endpoint['importSurveyMission'], data);

        if (response.success) {
          const taskId = response?.data?.task_id;

          // Only add to file management if there's a task_id (async operation)
          if (taskId) {
            await addListDownloadFile({
              id_file: fileKey,
              name: displayName,
              type: 'importMission',
              userId: currentUserId,
            });

            await addTaskIdToFile(taskId, fileKey, 'importMission', 'import');

            // Start polling in background
            pollTaskStatus({
              taskId,
              fileKey,
              displayName,
              type: 'importMission',
              onSuccess: options?.onSuccess,
              onError: options?.onError,
            }).catch((error) =>
              console.error(
                `Failed polling import mission task ${taskId}`,
                error,
              ),
            );
          } else {
            // No task_id means synchronous operation - call success callback directly
            options?.onSuccess?.();
          }

          return {
            success: true,
            message: response.message || t('Import mission started'),
            data: response.data,
          };
        }

        return {
          success: false,
          message: response.message || t('Something went wrong'),
        };
      } catch (error: any) {
        return {
          success: false,
          message: error.response?.data?.message || t('Something went wrong'),
        };
      }
    },
    [pollTaskStatus, currentUserId, t],
  );

  return {
    getSurveyMission,
    addSurveyMission,
    reviewSurveyMission,
    approveSurveyMission,
    rejectSurveyMission,
    activateSurveyMission,
    deactivateSurveyMission,
    getDetailSurveyMission,
    updateSurveyMission,
    checkPermissionActionSurveyMission,
    getListRouteForImportMission,
    importSurveyMissionAPI,
  };
};
