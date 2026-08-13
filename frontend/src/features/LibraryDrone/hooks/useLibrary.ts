import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';
import { SearchParam, SortParam } from '@/types/paramAPI';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import { LibraryListRequest, LibraryListResponse } from '../type';
import { convertLibraryData } from '../utils/convertData';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

const useLibrary = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const { convertDateFormatToUTC, convertDateFormatToYYYYMMDD, convertDateToUTCStartOfDay, convertDateToUTCEndOfDay } = useConvertDate();

  const logFormData = (formData: FormData) => {
    const entries = formData.entries();
    const result: Record<string, any> = {};
    for (const [key, value] of entries) {
      if (key === 'data') {
        result[key] = JSON.parse(value as string);
      } else {
        result[key] = value;
      }
    }
  };

  const getLibrary = async ({
    pageSize,
    currentPage,
    objSearch,
  }: LibraryListRequest): Promise<LibraryListResponse> => {
    try {
      showLoading();
      const params: {
        page_size: number;
        current_page: number;
        sort_obj?: SortParam[];
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
      const response = await API.get(endpoint.library, {
        params,
      });

      return {
        data:
          response.data.map((item: any) => ({
            id: item.id || '-',
            name: item.name || '-',
            created_on: item.created_on || '-',
            main_type__name: item.main_type__name || '-',
            note: item.note || '-',
            manufacturer: item.manufacturer || '-',
            model: item.model || '-',
            active: item.active,
            in_use: item.in_use > 0,
            group__name: item.group__name || '-',
            group__id: item.group__id || '-',
            notShowCheckbox: item.in_use > 0,
          })) || [],
        totalItem: response.total_items || 0,
        totalPage: response.total_pages || 0,
      };
    } catch {
      return {
        data: [],
        totalItem: 0,
        totalPage: 0,
      };
    } finally {
      hideLoading();
    }
  };

  const getLibraryById = async (id: number, edit = false) => {
    try {
      showLoading();
      const response = await API.get(
        endpoint.library + `/${id}?edit=${edit}&depth=2`,
      );

      return {
        data: response.data,
        success: true,
      };
    } catch (error: any) {
      return {
        message: error.response.data.message,
        success: false,
      };
    } finally {
      hideLoading();
    }
  };



  const createLibrary = async (data: FormData) => {
    // const files = data?.files;
    // const clonedFormData = JSON.parse(JSON.stringify(data));

    // if (Array.isArray(files)) {
    //     clonedFormData.files = files.filter(file => file instanceof File);
    // }
    // const status = clonedFormData.data?.manufacturer_information?.insurance_status;
    // if (status === false || status === "false") {
    //     clonedFormData.data.manufacturer_information.current_status = null;
    // }
    // const config = {
    //     headers: {
    //         "Content-Type": "multipart/form-data",
    //     },
    // };
    // const dataLibrary = convertLibraryData(clonedFormData);

    // const formData = new FormData();
    // const deleteFiles = true;
    // formData.append("replace_files", deleteFiles.toString());

    // formData.append("data", JSON.stringify(dataLibrary));

    // if (Array.isArray(clonedFormData.files)) {
    //     clonedFormData.files.forEach((file: File) => {
    //         formData.append(`files`, file);
    //     });
    // }
    const avatarFile = data?.avatar;
    const files = data?.files;
    const clonedFormData = JSON.parse(JSON.stringify(data));

    console.log('clonedFormData', clonedFormData);
    if (avatarFile instanceof File) {
      clonedFormData.avatar = avatarFile;
    }
    if (Array.isArray(files)) {
      clonedFormData.files = files.filter((file) => file instanceof File);
    }
    const status =
      clonedFormData.data?.manufacturer_information?.insurance_status;
    if (status === false || status === 'false') {
      clonedFormData.data.manufacturer_information.current_status = null;
    }
    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    };
    const dataDevice = convertLibraryData(clonedFormData, isRoleSuperuser, convertDateFormatToYYYYMMDD, convertDateToUTCStartOfDay, convertDateToUTCEndOfDay);

    const formData = new FormData();
    const deleteFiles = true;
    formData.append('replace_files', deleteFiles.toString());

    if (clonedFormData.avatar) {
      formData.append('avatar', clonedFormData.avatar);
    }

    formData.append('data', JSON.stringify(dataDevice));

    if (Array.isArray(clonedFormData.files)) {
      clonedFormData.files.forEach((file: File) => {
        formData.append(`files`, file);
      });
    }
    logFormData(formData);

    try {
      showLoading();
      const response = await API.post(endpoint.library, formData, config);

      return {
        message: response.message,
        success: true,
      };
    } catch (error: any) {
      return {
        message: error.response.data.message,
        success: false,
      };
    } finally {
      hideLoading();
    }
  };

  const deleteLibrary = async ({ ids }: { ids: string }) => {
    try {
      showLoading();
      const response = await API.delete(endpoint.deleteLibrary(ids), {
        params: {
          ids: ids,
        },
      });

      if (response.status) {
        return {
          message: response.message,
          success: true,
        };
      }
      return {
        message: response.message,
        success: false,
      };
    } catch (error: any) {
      return {
        message: error.response.data.message,
        success: false,
      };
    } finally {
      hideLoading();
    }
  };

  const updateLibrary = async (data: any) => {
    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    };
    const formData = new FormData();

    // Handle avatar - only send if it's a new file
    if (data.avatar && data.avatar instanceof File) {
      formData.append('avatar', data.avatar);
    }

    if (data.removedAvatar && !data.avatar) {
      formData.append('delete_avatar', data.removedAvatar);
    }

    // Handle attachments
    if (Array.isArray(data.files)) {
      const newFiles = data.files.filter((file: any) => file instanceof File);
      const existingFiles = data.files.filter(
        (file: any) => typeof file === 'object' && file.file_url,
      );
      const removedFiles = data.removedFiles || [];

      // If all existing files are removed and there are new files, set replace_files to true
      if (existingFiles.length === 0 && newFiles.length > 0) {
        formData.append('replace_files', 'true');
      } else if (removedFiles.length > 0) {
        // If only some files are removed, send their IDs
        formData.append('files_to_remove', removedFiles.join(', '));
      }

      // Append new files
      newFiles.forEach((file: File) => {
        formData.append('files', file);
      });
    }

    formData.append('data', JSON.stringify(data.data));

    logFormData(formData);

    try {
      showLoading();
      const response = await API.post(
        endpoint.library + `/${data.id}`,
        formData,
        config,
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

  return {
    getLibrary,
    getLibraryById,
    createLibrary,
    deleteLibrary,
    updateLibrary,
  };
};

export default useLibrary;
