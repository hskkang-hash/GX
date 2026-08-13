import { useCallback, useEffect, useState } from 'react';
import { ToastTopHelper } from 'rj-core';

import { useFileManagementStore } from '../store/FileManagement.store';
import {
  updateListDownloadFile,
  updateListFile,
} from '../utils/actionFileManagement';
import { setDownloadingFlag } from './useBeforeUnloadWarning';

interface WebSocketMessage {
  type: string;
  order_item_id?: number;
  order_item_ids?: number[];
  status: string;
  device_type?: string;
  notification_type?: string;
  message?: string;
  data?: {
    filename: string;
    download_url: string;
  };
}

/**
 * Ensures a URL uses HTTPS protocol instead of HTTP
 * @param url - The URL to enforce HTTPS on
 * @returns The URL with HTTPS protocol enforced
 */
const enforceHttps = (url: string): string => {
  // Don't modify blob URLs, data URLs, or relative URLs
  if (
    url.startsWith('blob:') ||
    url.startsWith('data:') ||
    url.startsWith('/') ||
    !url.includes('://')
  ) {
    return url;
  }

  // Replace http:// with https://
  if (url.startsWith('http://')) {
    return url.replace('http://', 'https://');
  }

  return url;
};

export const downloadFile = (filename: string, downloadUrl: string): void => {
  // Tạm thời disable cảnh báo trong quá trình download
  setDownloadingFlag(true);

  // Ensure the download URL uses HTTPS
  const secureUrl = enforceHttps(downloadUrl);

  const link = document.createElement('a');
  link.href = secureUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Only revoke object URL if it's a blob URL
  if (secureUrl.startsWith('blob:')) {
    window.URL.revokeObjectURL(secureUrl);
  }

  // Re-enable cảnh báo sau một khoảng thời gian ngắn
  setTimeout(() => {
    setDownloadingFlag(false);
  }, 1000);
};

export const useFileMessageHandler = () => {
  const [message, setMessage] = useState<WebSocketMessage | null>(null);

  const handleMessage = useCallback((newMessage: WebSocketMessage): void => {
    setMessage(newMessage);
  }, []);

  const getGXType = useCallback(
    (device_type?: string, notification_type?: string) => {
      return device_type === 'drone'
        ? notification_type === 'operational_video_upload'
          ? 'uploadVideoDrone'
          : 'uploadFileDrone'
        : notification_type === 'operational_video_upload'
          ? 'uploadVideoRobot'
          : 'uploadFileRobot';
    },
    [],
  );

  const getDownloadGXType = useCallback(
    (notification_type?: string, device_type?: string) => {
      if (notification_type === 'operational_data_download')
        return 'downloadFileAll';
      return device_type === 'drone'
        ? 'downloadFileDrone'
        : 'downloadFileRobot';
    },
    [],
  );

  const getDownloadStatus = useCallback((status: string) => {
    if (status === 'success') return 'done';
    if (status === 'pending' || status === 'processing') return 'uploading';
    return 'error';
  }, []);

  const handleUploadMessage = useCallback(
    async (msg: WebSocketMessage): Promise<void> => {
      const { order_item_id, status, device_type, notification_type } = msg;

      if (!order_item_id) return;

      const gxType = getGXType(device_type, notification_type);
      const newStatus = status === 'success' ? 'done' : 'error';

      await updateListFile({
        id_file: order_item_id,
        status: newStatus,
        type: gxType,
      });

      // Get current state to check if file exists
      const currentState = useFileManagementStore.getState();
      const file = currentState.fileManagement.find(
        (item) => item.gxId === order_item_id && item.gxType === gxType,
      );

      if (file) {
        if (status === 'success') {
          ToastTopHelper.success(msg.message || 'Upload successful');
          // Gọi callback của file nếu có
          if (file.onUploadSuccess) {
            await file.onUploadSuccess(file);
          }
        } else {
          ToastTopHelper.error(msg.message || 'Upload failed');
        }
      }
    },
    [getGXType],
  );

  const handleDownloadMessage = useCallback(
    (msg: WebSocketMessage): void => {
      const {
        order_item_ids,
        order_item_id,
        status,
        device_type,
        notification_type,
        data,
      } = msg;

      const id_file =
        notification_type === 'operational_data_download'
          ? order_item_ids?.join('-') || ''
          : `${order_item_id}`;

      const gxType = getDownloadGXType(notification_type, device_type);

      updateListDownloadFile({
        id_file,
        status: getDownloadStatus(status),
        type: gxType,
      });

      if (status === 'success' && data) {
        // Get current state to check if should auto download
        const currentState = useFileManagementStore.getState();
        const shouldAutoDownload = currentState.downloadFileManagement.some(
          (item) =>
            item.gxId === id_file &&
            (item.gxType === 'downloadFileAll' ||
              item.gxType === 'downloadFileDrone' ||
              item.gxType === 'downloadFileRobot'),
        );

        if (shouldAutoDownload) {
          downloadFile(data.filename, data.download_url);
        }
      }
    },
    [getDownloadGXType, getDownloadStatus, downloadFile],
  );

  useEffect(() => {
    if (!message) return;

    const { type } = message;

    console.log('message', message);

    // Handle upload messages
    if (
      type === 'operational_log_upload' ||
      type === 'operational_video_upload'
    ) {
      handleUploadMessage(message);
    }
    // Handle download messages
    else if (
      type === 'operational_data_download' ||
      type === 'operational_log_download'
    ) {
      handleDownloadMessage(message);
    }
  }, [message, handleUploadMessage, handleDownloadMessage]);

  return { handleMessage };
};
