import dayjs from 'dayjs';
import { useCallback, useMemo, useState } from 'react';
import { useLoadingContext, useUserInfo } from 'rj-core';

import { downloadFile } from '../../../hooks/useFileMessageHandler';
import i18n from '../../../i18n';
import API, { endpoint } from '../../../services/API';
import { useFileManagementStore } from '../../../store/FileManagement.store';
import {
  addListDownloadFile,
  addTaskIdToFile,
  removeFile,
  updateListDownloadFile,
} from '../../../utils/actionFileManagement';
import { NoticeManagementState } from '../types';
import { formatDateTime } from '../utils/dateFormat';
import { useDateTimeFormat } from './useDateFormat';

export const useHandover = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const userInfo = useUserInfo();
  const [sliderData, setSliderData] = useState<NoticeManagementState[]>([]);

  const { dateFormat, timeFormat, timezoneCode } = useDateTimeFormat();

  // Lấy userId hiện tại từ userInfo
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

  const pollTaskStatus = useCallback(
    async ({
      taskId,
      fileKey,
      displayName,
      type,
    }: {
      taskId?: string;
      fileKey: string;
      displayName: string;
      type: 'downloadFileAll' | 'downloadFileDrone' | 'downloadFileRobot';
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

      const maxAttempts = 60;
      const intervalMs = 5000;

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

              const finalFilename =
                statusData.filename || statusData.data?.filename || displayName;
              const downloadUrl =
                statusData.download_url || statusData.data?.download_url;

              if (downloadUrl) {
                downloadFile(finalFilename, downloadUrl);
              }
              return;
            }

            if (normalizedStatus === 'failed' || normalizedStatus === 'error') {
              await updateListDownloadFile({
                id_file: fileKey,
                status: 'error',
                type,
              });
              return;
            }
          }
        } catch (error) {
          console.error(`Error polling task status ${taskId}:`, error);
        }

        await wait(intervalMs);
      }
    },
    [wait, currentUserId],
  );

  const getSliderDataAPI = useCallback(async () => {
    try {
      showLoading();

      const params = {
        page_size: 1000000,
        current_page: 1,
        is_processed: false,
      };

      const response = await API.get(endpoint.noticeManagement, { params });

      const data = response?.data.map((item: NoticeManagementState) => ({
        ...item,
        content: item.content_text,
        created_time: formatDateTime(
          item.created_time,
          dateFormat,
          timeFormat,
          i18n.language,
          timezoneCode,
        ),
      }));

      setSliderData(data);
    } catch (error) {
      setSliderData([]);
    } finally {
      hideLoading();
    }
  }, [showLoading, hideLoading, dateFormat, timeFormat, timezoneCode]);

  const completeNoticeAPI = useCallback(
    async (id: number) => {
      try {
        showLoading();
        const response = await API.post(endpoint.noticeProcess, {
          id,
          is_processed: true,
        });
        return {
          success: response.success,
          message: response.message,
        };
      } catch (error) {
        return {
          success: false,
          message:
            (error as { response: { data: { message: string } } })?.response
              ?.data?.message || 'Something went wrong',
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading],
  );

  const deleteNoticeAPI = useCallback(
    async (id: number) => {
      try {
        showLoading();
        const response = await API.delete(endpoint.noticeManagement, {
          data: { id: id },
        });
        return {
          success: response.success,
          message: response.message,
        };
      } catch (error) {
        return {
          success: false,
          message:
            (error as { response: { data: { message: string } } })?.response
              ?.data?.message || 'Something went wrong',
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading],
  );

  const restoreNoticeAPI = useCallback(
    async (id: number) => {
      try {
        showLoading();
        const response = await API.post(endpoint.noticeRestore, {
          id,
        });
        return {
          success: response.success,
          message: response.message,
        };
      } catch (error) {
        return {
          success: false,
          message:
            (error as { response: { data: { message: string } } })?.response
              ?.data?.message || 'Something went wrong',
        };
      } finally {
        hideLoading();
      }
    },
    [showLoading, hideLoading],
  );

  const downloadHandoverAPI = useCallback(
    async ({
      start_date,
      end_date,
    }: {
      start_date: string;
      end_date: string;
    }) => {
      try {
        const fileKey = `${start_date}-${end_date}`;
        const displayName = `handover-${start_date}-${end_date}.pdf`;

        await addListDownloadFile({
          id_file: `${start_date}-${end_date}`,
          name: displayName,
          type: 'downloadFileAll',
          userId: currentUserId,
        });

        const response = await API.post(endpoint.downloadHandover, {
          start_date_time: start_date
            ? start_date
            : dayjs().subtract(7, 'day').format('YYYY-MM-DD'),
          end_date_time: end_date ? end_date : dayjs().format('YYYY-MM-DD'),
        });

        const taskId = response?.data?.task_id;
        await addTaskIdToFile(taskId, fileKey, 'downloadFileAll', 'download');

        pollTaskStatus({
          taskId,
          fileKey,
          displayName,
          type: 'downloadFileAll',
        }).catch((error) =>
          console.error(
            `Failed polling handover download task ${taskId}`,
            error,
          ),
        );

        return {
          success: true,
          message: response.message || 'File downloaded successfully',
        };
      } catch (error) {
        removeFile(`${start_date}-${end_date}`, 'downloadFileAll');
        return {
          success: false,
          message:
            (error as any)?.response?.data?.message ||
            'Failed to download file',
        };
      }
    },
    [pollTaskStatus],
  );

  const downloadNoticeAPI = useCallback(
    async ({
      selectedFields,
      start_date,
      end_date,
      objSearch,
    }: {
      start_date?: string;
      end_date?: string;
      selectedFields: string[];
      objSearch?: any;
    }) => {
      try {
        const fileKey = `${dayjs().format('YYYY-MM-DD')}-${selectedFields.join('-')}`;
        const displayName = `handover-${dayjs().format('YYYY-MM-DD')}-${selectedFields.join('-')}.csv`;

        await addListDownloadFile({
          id_file: fileKey,
          name: displayName,
          type: 'downloadFileAll',
          userId: currentUserId,
        });
        const body: {
          start_date_time?: string;
          end_date_time?: string;
          selected_field?: string[];
          [key: string]: any;
        } = {};
        if (start_date) {
          body.start_date_time = start_date;
        }
        if (end_date) {
          body.end_date_time = end_date;
        }
        if (selectedFields) {
          body.selected_field = selectedFields;
        }
        // Gửi tất cả các params search từ objSearch.searchParams (trừ page_size và current_page)
        if (objSearch) {
          if (objSearch.searchParams && Array.isArray(objSearch.searchParams)) {
            objSearch.searchParams.forEach(
              (item: { id: string; value: any }) => {
                // Bỏ qua page_size và current_page
                if (item.id !== 'page_size' && item.id !== 'current_page') {
                  body[item.id] = item.value;
                }
              },
            );
          }
          if (objSearch.sortParams && objSearch.sortParams.length) {
            body.sort_obj = objSearch.sortParams;
          }
        }
        const response = await API.post(endpoint.downloadNotice, body);

        if (response.success) {
          const taskId = response?.data?.task_id;
          await addTaskIdToFile(taskId, fileKey, 'downloadFileAll', 'download');

          pollTaskStatus({
            taskId,
            fileKey,
            displayName,
            type: 'downloadFileAll',
          }).catch((error) =>
            console.error(
              `Failed polling notice download task ${taskId}`,
              error,
            ),
          );

          return {
            success: true,
            message: response.message || 'File downloaded successfully',
          };
        }

        removeFile(fileKey, 'downloadFileAll');
        return {
          success: false,
          message: response.message || 'Failed to download file',
        };
      } catch (error) {
        removeFile(
          `${dayjs().format('YYYY-MM-DD')}-${selectedFields.join('-')}`,
          'downloadFileAll',
        );
        return {
          success: false,
          message:
            (error as any)?.response?.data?.message ||
            'Failed to download file',
        };
      }
    },
    [pollTaskStatus, currentUserId],
  );

  const downloadCompletedNoticeAPI = useCallback(
    async ({
      start_date,
      end_date,
      selectedFields,
      objSearch,
    }: {
      start_date?: string;
      end_date?: string;
      selectedFields: string[];
      objSearch?: any;
    }) => {
      try {
        const fileKey = `${dayjs().format('YYYY-MM-DD')}-${selectedFields.join('-')}-completed`;
        const displayName = `handover-${dayjs().format('YYYY-MM-DD')}-${selectedFields.join('-')}-completed.csv`;

        await addListDownloadFile({
          id_file: fileKey,
          name: displayName,
          type: 'downloadFileAll',
          userId: currentUserId,
        });
        const body: {
          start_date_time?: string;
          end_date_time?: string;
          selected_field?: string[];
          [key: string]: any;
        } = {};
        if (start_date) {
          body.start_date_time = start_date;
        }
        if (end_date) {
          body.end_date_time = end_date;
        }
        if (selectedFields) {
          body.selected_field = selectedFields;
        }
        // Gửi tất cả các params search từ objSearch.searchParams (trừ page_size và current_page)
        if (objSearch) {
          if (objSearch.searchParams && Array.isArray(objSearch.searchParams)) {
            objSearch.searchParams.forEach(
              (item: { id: string; value: any }) => {
                // Bỏ qua page_size và current_page
                if (item.id !== 'page_size' && item.id !== 'current_page') {
                  body[item.id] = item.value;
                }
              },
            );
          }
          if (objSearch.sortParams && objSearch.sortParams.length) {
            body.sort_obj = objSearch.sortParams;
          }
        }
        const response = await API.post(endpoint.downloadCompletedNotice, body);
        if (response.success) {
          const taskId = response?.data?.task_id;
          await addTaskIdToFile(taskId, fileKey, 'downloadFileAll', 'download');

          pollTaskStatus({
            taskId,
            fileKey,
            displayName,
            type: 'downloadFileAll',
          }).catch((error) =>
            console.error(
              `Failed polling completed notice download task ${taskId}`,
              error,
            ),
          );
          return {
            success: true,
            message: response.message || 'File downloaded successfully',
          };
        }

        removeFile(fileKey, 'downloadFileAll');
        return {
          success: false,
          message: response.message || 'Failed to download file',
        };
      } catch (error) {
        removeFile(
          `${dayjs().format('YYYY-MM-DD')}-${selectedFields.join('-')}`,
          'downloadFileAll',
        );
        return {
          success: false,
          message:
            (error as any)?.response?.data?.message ||
            'Failed to download file',
        };
      }
    },
    [pollTaskStatus, currentUserId],
  );
  return {
    sliderData,
    getSliderDataAPI,
    completeNoticeAPI,
    deleteNoticeAPI,
    restoreNoticeAPI,
    downloadHandoverAPI,
    downloadNoticeAPI,
    downloadCompletedNoticeAPI,
  };
};
