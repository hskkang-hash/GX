import dayjs from 'dayjs';
import { useMemo } from 'react';
import { useLoadingContext, useUserInfo } from 'rj-core';

import API, { endpoint } from '../../../services/API';
import {
  addListDownloadFile,
  addTaskIdToFile,
  removeFile,
  uploadFile,
} from '../../../utils/actionFileManagement';

interface DeviceParams {
  page_size: number;
  current_page: number;
  depth: number;
  created_on_start?: string;
  created_on_end?: string;
  main_type__name?: string;
  [key: string]: any;
}
const useAPI = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const userInfo = useUserInfo();

  // Lấy userId hiện tại từ userInfo
  const currentUserId = useMemo(() => {
    if (!userInfo) return undefined;
    return (
      (userInfo as { user_id?: number | string })?.user_id ||
      (userInfo as { id?: number | string })?.id ||
      undefined
    );
  }, [userInfo]);

  const getOperationalData = async ({
    pageSize = 25,
    currentPage = 1,
    objSearch = {},
  }: {
    pageSize?: number;
    currentPage?: number;
    objSearch?: any;
  }) => {
    const params: DeviceParams = {
      page_size: pageSize,
      current_page: currentPage,
      depth: 2,
    };
    if (objSearch) {
      if (objSearch?.startDate) {
        params['created_on_start'] = dayjs(objSearch.startDate).format(
          'YYYY-MM-DD HH:mm:ss',
        );
      }
      if (objSearch?.endDate) {
        params['created_on_end'] = dayjs(objSearch.endDate).format(
          'YYYY-MM-DD HH:mm:ss',
        );
      }
      if (objSearch?.searchParams) {
        objSearch?.searchParams.forEach((item: any) => {
          if (item.id === 'main_type') {
            params['main_type__name'] = item.value;
          } else if (item.value == 'Select' || item.value == '선택') {
            params['status__name'] = '';
          } else {
            params[item.id] = item.value;
          }
        });
      }
      if (objSearch?.filters) {
        params['filters'] = objSearch.filters;
      }
      if (objSearch?.sortParams && objSearch?.sortParams.length) {
        params.sort_obj = objSearch.sortParams;
      }
    }
    try {
      showLoading();
      const response = await API.get(endpoint.operationalData, { params });
      return {
        success: true,
        data: {
          data: response.data.map((item: any) => ({
            ...item,
          })),
          totalItem: response.total_items,
          totalPage: response.total_pages,
        },
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
        data: {
          data: [],
          totalItem: 0,
          totalPage: 0,
        },
      };
    } finally {
      hideLoading();
    }
  };

  const uploadFileOperationalData = async ({
    id,
    files,
    type,
  }: {
    id: number;
    files: any;
    type:
      | 'uploadFileDrone'
      | 'uploadFileRobot'
      | 'uploadVideoDrone'
      | 'uploadVideoRobot';
  }) => {
    // Pass useOperationalDataEndpoint=true to use checkTaskOperationalData endpoint
    uploadFile(files, id, type, currentUserId, undefined, true);
    const formData = new FormData();
    Array.from(files).forEach((file: any) => {
      formData.append('files', file);
    });
    try {
      const response = await API.post(endpoint[type](id), formData);

      console.log('taskId', response?.data?.task_id);
      const taskId = response?.data?.task_id;
      addTaskIdToFile(taskId, id, type, 'upload');
      return {
        success: true,
        message: response.message,
      };
    } catch (error: any) {
      removeFile(id, type);
      return {
        success: false,
        message: error.response.data.message,
      };
    }
  };

  const donwloadFileOperationalData = async ({
    id,
    type,
    delivery_operation_code,
  }: {
    id: number;
    type: 'downloadFileDrone' | 'downloadFileRobot';
    delivery_operation_code: string;
  }) => {
    try {
      // Pass useOperationalDataEndpoint=true to use checkTaskOperationalData endpoint
      addListDownloadFile({
        id_file: id.toString(),
        name:
          type === 'downloadFileDrone'
            ? `operational_logs_drone__${delivery_operation_code}.zip`
            : `operational_logs_robot__${delivery_operation_code}.zip`,
        type: type,
        userId: currentUserId,
        useOperationalDataEndpoint: true,
      });
      const response = await API.get(endpoint[type](id));

      console.log('response', response);

      const taskId = response?.data?.download_task_id;
      console.log('taskId', taskId);
      addTaskIdToFile(taskId, id.toString(), type, 'download');

      return {
        success: true,
        message: response.message || 'File downloaded successfully',
      };
    } catch (error: any) {
      removeFile(id.toString(), type);
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message || 'Failed to download file',
      };
    } finally {
      hideLoading();
    }
  };

  const donwloadFileOperationalDataAll = async ({ id }: { id: number[] }) => {
    const params = new URLSearchParams();

    id.forEach((id) => {
      params.append('order_item_ids', String(id));
    });

    try {
      // Pass useOperationalDataEndpoint=true to use checkTaskOperationalData endpoint
      addListDownloadFile({
        id_file: id.join('-'),
        name: 'operational_data_bulk_download.zip',
        type: 'downloadFileAll',
        userId: currentUserId,
        useOperationalDataEndpoint: true,
      });
      const response = await API.get(
        endpoint.downloadFileOperationalDataAll + '?' + params.toString(),
      );

      console.log('response', response);

      const taskId = response?.data?.download_task_id;
      console.log('taskId', taskId);
      addTaskIdToFile(taskId, id.join('-'), 'downloadFileAll', 'download');

      return {
        success: true,
        message: response?.message || 'File downloaded successfully',
      };
    } catch (error: any) {
      removeFile(id.join('-'), 'downloadFileAll');
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message || 'Failed to download file',
      };
    } finally {
      hideLoading();
    }
  };

  const getDetailOperationalData = async (id: number) => {
    try {
      showLoading();
      const response = await API.get(endpoint.detailOperationalData(id));
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message ||
          'An unknown error occurred',
        data: {
          data: [],
        },
      };
    } finally {
      hideLoading();
    }
  };

  return {
    getOperationalData,
    getDetailOperationalData,
    uploadFileOperationalData,
    donwloadFileOperationalData,
    donwloadFileOperationalDataAll,
  };
};

export default useAPI;
