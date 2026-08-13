import { useMemo } from 'react';
import { useLoadingContext, useUserInfo } from 'rj-core';

import API, { endpoint } from '../../../services/API';
import {
  addTaskIdToFile,
  removeFile,
  uploadFile,
} from '../../../utils/actionFileManagement';
import { ExportRouteParams, ExportRouteResult } from './types';

export const useRoute = () => {
  const currentLanguage = localStorage.getItem('language');
  const { showLoading, hideLoading, showLoadingGlobal, hideLoadingGlobal } =
    useLoadingContext();
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

  const getDefaultCMD = async (search_name: string) => {
    try {
      const response = await API.get(endpoint.commands, {
        params: {
          searchTerm: search_name || '',
        },
      });

      return {
        options:
          response.data.commands?.length > 0
            ? response.data.commands
                .map((item: { CommandName: string; CommandId: string }) => {
                  if (
                    item.CommandName.toLowerCase() ===
                      'WAYPOINT'.toLowerCase() ||
                    item.CommandName.toLowerCase() ===
                      'NAV_WAYPOINT'.toLowerCase()
                  ) {
                    return {
                      label: item.CommandName,
                      value: item.CommandId,
                    };
                  }
                  return null;
                })
                .filter(Boolean)
            : [],
      };
    } catch (error: any) {
      return {
        success: false,
        options: [],
        message: error.response.data.message,
      };
    }
  };

  const getDefaultTakeoffCMD = async () => {
    try {
      const response = await API.get(endpoint.commands, {
        params: {
          searchTerm: 'NAV_TAKEOFF',
        },
      });

      return {
        options:
          response.data.commands?.length > 0
            ? response.data.commands
                .map((item: { CommandName: string; CommandId: string }) => {
                  if (
                    item.CommandName.toLowerCase() ===
                      'NAV_TAKEOFF'.toLowerCase() ||
                    item.CommandName.toLowerCase() === 'TAKEOFF'.toLowerCase()
                  ) {
                    return {
                      label: item.CommandName,
                      value: item.CommandId,
                    };
                  }
                  return null;
                })
                .filter(Boolean)
            : [],
      };
    } catch (error: any) {
      return {
        success: false,
        options: [],
        message: error.response.data.message,
      };
    }
  };

  const getDefaultFrame = async (search_name: string) => {
    try {
      const response = await API.get(endpoint.frames, {
        params: {
          searchTerm: search_name || '',
        },
      });

      return {
        options:
          response.data.frames?.length > 0
            ? response.data.frames
                .map((item: { FrameName: string; FrameId: string }) => {
                  if (
                    item.FrameName.toLowerCase() === search_name.toLowerCase()
                  ) {
                    return {
                      label: item.FrameName,
                      value: item.FrameId,
                    };
                  }
                  return null;
                })
                .filter(Boolean)
            : [],
      };
    } catch (error: any) {
      return {
        success: false,
        options: [],
        message: error.response.data.message,
      };
    }
  };

  const getOptionsCMD = () => {
    return async (
      search: string,
      loadedOptions: any,
      { page }: { page: number },
    ) => {
      console.log({ search, page });

      const response = await API.get(endpoint.commands, {
        params: {
          searchTerm: search || '',
          page: page ?? 1,
          pageSize: 10,
        },
      });

      const data = response.data || [];
      const hasMore = data.pagination.has_next_page;

      return {
        options: data?.commands?.map(
          (item: { CommandName: string; CommandId: string }) => ({
            label: item.CommandName,
            value: item.CommandId,
          }),
        ),
        hasMore,
        additional: {
          page: (page ?? 1) + 1,
        },
      };
    };
  };

  const getOptionsFrame = () => {
    return async (
      search: string,
      loadedOptions: any,
      { page }: { page: number },
    ) => {
      const response = await API.get(endpoint.frames, {
        params: {
          searchTerm: search || '',
          page: page ?? 1,
          pageSize: 10,
        },
      });

      const data = response.data || [];
      const hasMore = data.pagination.has_next_page;

      return {
        options: data?.frames?.map(
          (item: { FrameName: string; FrameId: string }) => ({
            label: item.FrameName,
            value: item.FrameId,
          }),
        ),
        hasMore,
        additional: {
          page: (page ?? 1) + 1,
        },
      };
    };
  };

  const importRoute = async (
    data: { files: File[] | File; service?: { value: number | string } | null },
    id: number,
    onSuccess?: () => void | Promise<void>,
  ) => {
    try {
      showLoadingGlobal();
      const formData = new FormData();
      const file = Array.isArray(data.files) ? data.files[0] : data.files;
      if (!file) {
        throw new Error('No file provided');
      }
      uploadFile([file], id, 'importFileAll', currentUserId, onSuccess);
      formData.append('file', file);
      if (data.service?.value !== undefined && data.service?.value !== null) {
        formData.append('route_service_id', String(data.service.value));
      }

      const response = await API.post(endpoint.importRoute, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.success) {
        const taskId = response?.data?.task_id;
        addTaskIdToFile(taskId, id, 'importFileAll', 'upload');
      }

      return {
        success: response.success,
        message:
          currentLanguage === 'en'
            ? response?.message?.en
            : currentLanguage === 'ko'
              ? response?.message?.ko
              : response?.message?.th,
      };
    } catch (error: any) {
      removeFile(id, 'importFileAll');
      return {
        success: false,
        message:
          currentLanguage === 'en'
            ? error.response?.data?.message?.en || 'Failed to upload file'
            : currentLanguage === 'ko'
              ? error.response?.data?.message?.ko ||
                '파일 업로드에 실패했습니다'
              : error.response?.data?.message?.th || 'การอัปโหลดไฟล์ล้มเหลว',
      };
    } finally {
      hideLoadingGlobal();
    }
  };

  const importRoutes = async (
    data: { files: File[]; service?: { value: number | string } | null },
    id: number,
    onSuccess?: () => void | Promise<void>,
  ) => {
    try {
      showLoadingGlobal();
      const formData = new FormData();

      // Ensure files is an array
      const filesArray = Array.isArray(data.files) ? data.files : [data.files];

      if (filesArray.length === 0) {
        throw new Error('No files provided');
      }

      // Append each file to FormData
      filesArray.forEach((file) => {
        formData.append('files', file);
      });
      if (data.service?.value !== undefined && data.service?.value !== null) {
        formData.append('route_service_id', String(data.service.value));
      }

      // Create individual file management entries for each file
      filesArray.forEach((file, index) => {
        const fileId = id + index; // Unique ID for each file
        uploadFile([file], fileId, 'importFileAll', currentUserId, onSuccess);
      });

      const response = await API.post(endpoint.importRoutes, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.success) {
        // Handle multiple task IDs from accepted files
        const accepted = response?.data?.accepted || [];
        const rejected = response?.data?.rejected || [];

        // Match accepted files with their file entries by filename
        accepted.forEach((item: any) => {
          if (item.task_id && item.file_name) {
            // Find the index of the file with matching name
            const fileIndex = filesArray.findIndex(
              (file) => file.name === item.file_name,
            );
            if (fileIndex !== -1) {
              const fileId = id + fileIndex;
              addTaskIdToFile(item.task_id, fileId, 'importFileAll', 'upload');
            }
          }
        });

        // Remove file entries for rejected files
        rejected.forEach((item: any) => {
          if (item.file_name) {
            const fileIndex = filesArray.findIndex(
              (file) => file.name === item.file_name,
            );
            if (fileIndex !== -1) {
              const fileId = id + fileIndex;
              removeFile(fileId, 'importFileAll');
            }
          }
        });
      } else {
        // Remove all file entries on failure
        filesArray.forEach((file, index) => {
          const fileId = id + index;
          removeFile(fileId, 'importFileAll');
        });
      }

      return {
        success: response.success,
        message:
          currentLanguage === 'en'
            ? response?.message?.en
            : currentLanguage === 'ko'
              ? response?.message?.ko
              : response?.message?.th,
        data: response.data,
      };
    } catch (error: any) {
      // Remove all file entries on error
      const filesArray = Array.isArray(data.files) ? data.files : [data.files];
      filesArray.forEach((file, index) => {
        const fileId = id + index;
        removeFile(fileId, 'importFileAll');
      });
      return {
        success: false,
        message:
          currentLanguage === 'en'
            ? error.response?.data?.message?.en || 'Failed to upload files'
            : currentLanguage === 'ko'
              ? error.response?.data?.message?.ko ||
                '파일 업로드에 실패했습니다'
              : error.response?.data?.message?.th || 'การอัปโหลดไฟล์ล้มเหลว',
      };
    } finally {
      hideLoadingGlobal();
    }
  };

  const exportRoute = async ({
    route_ids,
  }: ExportRouteParams): Promise<ExportRouteResult> => {
    try {
      showLoading();
      const response = await API.post(
        endpoint.exportRoute,
        {
          route_ids,
        },
        {
          responseType: 'blob',
        },
      );

      if (response instanceof Blob) {
        const fileName = `routes-export-${Date.now()}-${Math.random().toString(36).substring(2, 15)}.zip`;
        const url = window.URL.createObjectURL(response);

        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        window.URL.revokeObjectURL(url);

        return {
          success: true,
          message:
            currentLanguage === 'en'
              ? 'File downloaded successfully'
              : currentLanguage === 'ko'
                ? '파일이 성공적으로 다운로드되었습니다'
                : 'การดาวน์โหลดไฟล์สำเร็จ',
        };
      }

      return {
        success: false,
        message:
          currentLanguage === 'en'
            ? 'Invalid response format from server'
            : currentLanguage === 'ko'
              ? '서버에서 잘못된 응답 형식'
              : 'รูปแบบการตอบกลับจากเซิร์ฟเวอร์ไม่ถูกต้ออัปโหลดไฟล์ล้มเหลว',
      };
    } catch (error: any) {
      return {
        success: false,
        message:
          currentLanguage === 'en'
            ? error.response?.data?.message['en'] || 'Failed to export routes'
            : currentLanguage === 'ko'
              ? error.response?.data?.message['ko'] ||
                '경로 내보내기에 실패했습니다'
              : error.response?.data?.message['th'] ||
                '경로 내보내기에 실패했습니다',
      };
    } finally {
      hideLoading();
    }
  };

  const deleteRoute = async (ids: string) => {
    try {
      showLoading();
      const response = await API.delete(endpoint.deleteRoute(ids));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      hideLoading();
    }
  };

  return {
    getOptionsCMD,
    getOptionsFrame,

    getDefaultCMD,
    getDefaultFrame,
    getDefaultTakeoffCMD,

    importRoute,
    importRoutes,
    exportRoute,
    deleteRoute,
  };
};
