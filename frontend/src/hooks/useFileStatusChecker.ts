import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useUserInfo } from 'rj-core';

import {
  GXDownloadFile,
  GXUploadFile,
  useFileManagementStore,
} from '../store/FileManagement.store';
import {
  updateListFile,
  updateListDownloadFile,
} from '../utils/actionFileManagement';
import { useFileManagement } from './useFileManagement';
import { downloadFile } from './useFileMessageHandler';

interface FileStatusResponse {
  status?: string;
  message?: string;
  download_url?: string;
  file_url?: string;
  filename?: string;
  file_id?: string;
  record_count?: number;
  error_code?: string;
  progress_percentage?: number;
  error_details?: {
    name?: string;
    filename?: string;
    [key: string]: unknown;
  };
  data?: {
    download_url?: string;
    file_url?: string;
    filename?: string;
    file_id?: string;
    total_records?: number;
    progress_percentage?: number;
    [key: string]: unknown;
  };
}

export const useFileStatusChecker = (): void => {
  const { checkTaskSocket, checkTaskOperationalData } = useFileManagement();
  const { fileManagement, downloadFileManagement } = useFileManagementStore();
  const userInfo = useUserInfo();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Lấy userId hiện tại từ userInfo
  const currentUserId = useMemo(() => {
    if (!userInfo) return null;
    return (
      (userInfo as { user_id?: number | string })?.user_id ||
      (userInfo as { id?: number | string })?.id ||
      null
    );
  }, [userInfo]);

  const checkFileStatus = useCallback(async (): Promise<void> => {
    // Lấy danh sách file đang upload (chưa done) và chỉ của user hiện tại
    const processingUploadFiles = fileManagement.filter(
      (file: GXUploadFile) => {
        if (file.status !== 'uploading' || !file.taskId) return false;
        // Nếu có userId, chỉ lấy files của user hiện tại
        if (currentUserId !== null && file.userId) {
          return (
            file.userId === currentUserId ||
            String(file.userId) === String(currentUserId)
          );
        }
        // Nếu không có userId (backward compatibility), chỉ lấy nếu currentUserId cũng null
        return currentUserId === null;
      },
    );

    const processingDownloadFiles = downloadFileManagement.filter(
      (file: GXDownloadFile) => {
        if (file.status !== 'uploading' || !file.taskId) return false;
        // Nếu có userId, chỉ lấy files của user hiện tại
        if (currentUserId !== null && file.userId) {
          return (
            file.userId === currentUserId ||
            String(file.userId) === String(currentUserId)
          );
        }
        // Nếu không có userId (backward compatibility), chỉ lấy nếu currentUserId cũng null
        return currentUserId === null;
      },
    );

    // Kiểm tra trạng thái cho upload files
    for (const file of processingUploadFiles) {
      if (file.taskId) {
        try {
          // Use checkTaskOperationalData if flag is set, otherwise checkTaskSocket
          const response = file.useOperationalDataEndpoint
            ? await checkTaskOperationalData(file.taskId)
            : await checkTaskSocket(file.taskId);
          if (response.success && response.data) {
            const statusData = response.data as FileStatusResponse;

            // Extract progress percentage from API response
            const progress =
              statusData?.progress_percentage ??
              statusData?.data?.progress_percentage;

            // Cập nhật trạng thái file dựa trên response
            let newStatus: 'uploading' | 'done' | 'error' = 'uploading';

            if (
              statusData.status === 'completed' ||
              statusData.status === 'success'
            ) {
              newStatus = 'done';
            } else if (
              statusData.status === 'failed' ||
              statusData.status === 'error'
            ) {
              newStatus = 'error';
            }

            // Update progress and status (always update progress even if status unchanged)
            const statusChanged = newStatus !== file.status;
            const progressChanged = progress !== undefined && progress !== file.progress;

            if (statusChanged || progressChanged) {
              const wasUploading = file.status === 'uploading';
              await updateListFile({
                id_file: file.gxId,
                status: newStatus,
                type: file.gxType,
                progress,
              });

              // Gọi callback nếu upload thành công
              if (newStatus === 'done' && wasUploading) {
                const currentState = useFileManagementStore.getState();
                // Lấy file đã được cập nhật từ store
                const updatedFile = currentState.fileManagement.find(
                  (f) => f.gxId === file.gxId && f.gxType === file.gxType,
                );
                if (updatedFile && updatedFile.onUploadSuccess) {
                  await updatedFile.onUploadSuccess(updatedFile);
                }
              }
            }
          }
        } catch (error) {
          console.error(
            `Error checking status for upload file ${file.taskId}:`,
            error,
          );
          // Cập nhật status thành error khi API call thất bại
          if (file.status !== 'error') {
            await updateListFile({
              id_file: file.gxId,
              status: 'error',
              type: file.gxType,
            });
          }
        }
      }
    }

    // Kiểm tra trạng thái cho download files
    for (const file of processingDownloadFiles) {
      if (file.taskId) {
        try {
          // Use checkTaskOperationalData if flag is set, otherwise checkTaskSocket
          const response = file.useOperationalDataEndpoint
            ? await checkTaskOperationalData(file.taskId)
            : await checkTaskSocket(file.taskId);
          if (response.success && response.data) {
            const statusData = response.data as FileStatusResponse;

            // Extract progress percentage from API response
            const progress =
              statusData?.progress_percentage ??
              statusData?.data?.progress_percentage;

            // Cập nhật trạng thái file dựa trên response
            let newStatus: 'uploading' | 'done' | 'error' = 'uploading';

            if (
              statusData.status === 'completed' ||
              statusData.status === 'success'
            ) {
              newStatus = 'done';
              const filename =
                statusData?.filename ||
                statusData?.data?.filename ||
                statusData?.error_details?.filename ||
                statusData?.error_details?.name ||
                '';
              let downloadUrl =
                statusData?.download_url ||
                statusData?.data?.download_url ||
                '';

              // Ensure HTTPS is used for download URLs
              if (downloadUrl && downloadUrl.startsWith('http://')) {
                downloadUrl = downloadUrl.replace('http://', 'https://');
              }

              if (filename && downloadUrl) {
                downloadFile(filename, downloadUrl);
              }
            } else if (
              statusData.status === 'failed' ||
              statusData.status === 'error'
            ) {
              newStatus = 'error';
            }

            // Update progress and status (always update progress even if status unchanged)
            const statusChanged = newStatus !== file.status;
            const progressChanged = progress !== undefined && progress !== file.progress;

            if (statusChanged || progressChanged) {
              await updateListDownloadFile({
                id_file: file.gxId,
                status: newStatus,
                type: file.gxType,
                progress,
              });
            }
          }
        } catch (error) {
          console.error(
            `Error checking status for download file ${file.taskId}:`,
            error,
          );
          // Cập nhật status thành error khi API call thất bại
          if (file.status !== 'error') {
            await updateListDownloadFile({
              id_file: file.gxId,
              status: 'error',
              type: file.gxType,
            });
          }
        }
      }
    }
  }, [
    fileManagement,
    downloadFileManagement,
    checkTaskSocket,
    checkTaskOperationalData,
    currentUserId,
  ]);

  useEffect(() => {
    // Kiểm tra xem có file nào đang processing không (chỉ của user hiện tại)
    const hasProcessingFiles =
      fileManagement.some((file: GXUploadFile) => {
        if (file.status !== 'uploading' || !file.taskId) return false;
        if (currentUserId !== null && file.userId) {
          return (
            file.userId === currentUserId ||
            String(file.userId) === String(currentUserId)
          );
        }
        return currentUserId === null;
      }) ||
      downloadFileManagement.some((file: GXDownloadFile) => {
        if (file.status !== 'uploading' || !file.taskId) return false;
        if (currentUserId !== null && file.userId) {
          return (
            file.userId === currentUserId ||
            String(file.userId) === String(currentUserId)
          );
        }
        return currentUserId === null;
      });

    if (hasProcessingFiles) {
      // Bắt đầu interval nếu chưa có
      if (!intervalRef.current) {
        intervalRef.current = setInterval(checkFileStatus, 5000); // 5 giây
      }
    } else {
      // Dừng interval nếu không có file nào đang processing
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    // Cleanup function
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fileManagement, downloadFileManagement, checkFileStatus, currentUserId]);

  // Cleanup khi component unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);
};
