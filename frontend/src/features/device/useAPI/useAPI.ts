import dayjs from 'dayjs';
import { useLoadingContext } from 'rj-core';

import { convertDeviceData } from '@/utils/deviceDataConverter';

import API, { endpoint } from '../../../services/API';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

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

  const deleteDevices = async ({
    ids,
  }: {
    ids?: string;
  }): Promise<{ success: boolean; message: any }> => {
    try {
      showLoading();
      const response = await API.delete(endpoint.deleteDevices(ids as string));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message || 'Something went wrong',
      };
    } finally {
      hideLoading();
    }
  };

  const getDeviceManagement = async ({
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
      const response = await API.get(endpoint.deviceManagement, { params });
      return {
        success: true,
        data: {
          data: response.data.map((item: any) => ({
            ...item,
            // data:
            // response.data.map((item: any) => ({
            //   id: item.id || '-',
            //   name: item.name || '-',
            //   created_on: item.created_on || '-',
            //   main_type__name: item.main_type__name || '-',
            //   note: item.note || '-',
            //   manufacturer: item.manufacturer || '-',
            //   model: item.model || '-',
            //   active: item.active,
            // in_use: item.in_use > 0,
            // notShowCheckbox: item.in_use > 0,
            // })) || [],
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

  const actionDevice = async ({
    ids,
    useLoading = false,
  }: {
    ids?: string;
    useLoading?: boolean;
  }): Promise<{ success: boolean; message: any }> => {
    if (!ids) {
      return {
        success: false,
        message: 'ID is required',
      };
    }
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.activeDeactiveDevice(ids));
      if (response.success) {
        return {
          success: true,
          message: response.message,
        };
      }
      return {
        success: false,
        message: response.message ?? 'Operation failed',
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message ?? 'Unexpected error',
      };
    } finally {
      useLoading && hideLoading();
    }
  };

  const getDetailDevice = async ({
    id,
    edit,
  }: {
    id: number;
    edit: boolean;
  }) => {
    try {
      showLoading();
      const response = await API.get(endpoint.detailDevice(id, edit));

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

  // Hàm chuyển đổi file object thành File instance
  const convertToFileInstances = async (fileObjects: any[]) => {
    if (!Array.isArray(fileObjects)) {
      return [];
    }

    const filePromises = fileObjects.map(async (fileObj) => {
      console.log('fileObj_convertToFileInstances', fileObj);
      console.log('fileObj_convertToFileInstances_url', fileObj.file_url);
      if (fileObj.file_url === 'null') {
        null;
      }
      try {
        // Fetch file content từ URL
        const response = await fetch(fileObj.file_url);

        if (!response.ok) {
          throw new Error(`Failed to fetch file: ${fileObj.file_name}`);
        }

        // Chuyển response thành blob
        const blob = await response.blob();

        // Tạo File instance từ blob
        const file = new File([blob], fileObj.file_name, {
          type: fileObj.file_type,
          lastModified: new Date(fileObj.created_on).getTime(),
        });

        return file;
      } catch (error) {
        console.error(`Error converting file ${fileObj.file_name}:`, error);
        return null;
      }
    });

    // Đợi tất cả promises hoàn thành và lọc bỏ null values
    const files = await Promise.all(filePromises);
    return files.filter((file) => file !== null);
  };

  // Cách sử dụng trong createDevice function
  const createDevice = async (data: any, dateFormat: string | null = null) => {
    const avatarFile = data?.avatar;
    let files = data?.files;

    // Chuyển đổi file objects thành File instances nếu cần
    if (
      Array.isArray(files) &&
      files.length > 0 &&
      !(files[0] instanceof File)
    ) {
      console.log('Converting file objects to File instances...');
      console.log('files_createDevice', files);
      files = await convertToFileInstances(files);
      console.log('Converted files:', files);
    }

    const clonedFormData = JSON.parse(JSON.stringify(data));

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

    const dataDevice = convertDeviceData(clonedFormData, isRoleSuperuser, convertDateFormatToYYYYMMDD, convertDateToUTCStartOfDay, convertDateToUTCEndOfDay);
    console.log('dataDevice_add_li', dataDevice);

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
      const response = await API.post(
        endpoint.deviceManagement,
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
  const updateDevice = async (data: any) => {
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

    if (data.delete_avatar && !data.avatar) {
      formData.append('delete_avatar', data.delete_avatar);
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
        endpoint.detailDevice(data.id, false),
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

  const changeStatusDevice = async ({ id }: { id: number }) => {
    try {
      showLoading();
      const response = await API.post(endpoint.changeStatusDrone(id), { id });

      if (response.success) {
        return {
          success: true,
          message: response.message,
          data: response,
        };
      }
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message || 'An error occurred',
      };
    } finally {
      hideLoading();
    }
  };

  const getDrones = ({
    key = 'name',
    value = 'id',
  }: { key?: string; value?: string } = {}) => {
    return async (
      search: string,
      loadedOptions: any[],
      { page }: { page: number } = { page: 1 },
    ) => {
      try {
        const response = await API.get(endpoint.getDrones, {
          params: {
            page_number: page ?? 1,
            page_size: 10,
            search_field: search,
          },
        });

        const data = response?.data?.drones || [];
        const hasMore = data.length === 10;
        // const hasMore = response?.data?.pagination
        //     ? response?.data?.pagination.current_page < response?.data?.pagination.total_pages
        //     : data.length === 2;
        // const hasMore = response?.data?.pagination?.current_page <= response?.data?.pagination?.total_pages;
        // const fakeData = [
        //   {
        //     UniqueId: "D-1234567890343443534534",
        //   },
        //   {
        //     UniqueId: "D-1234567891343434534534",
        //   },
        //   {
        //     UniqueId: "D-1234567892345345435345",
        //   },
        //   {
        //     UniqueId: "D-123456789334534534534",
        //   },
        //   {
        //     UniqueId: "D-123456783494",
        //   },
        //   {
        //     UniqueId: "D-123456734895 ",
        //   },
        //   {
        //     UniqueId: "D-123456347896",
        //   },
        //   {
        //     UniqueId: "D-123456347897",
        //   },
        //   {
        //     UniqueId: "D-123453467898",
        //   },
        //   {
        //     UniqueId: "D-123453467894",
        //   },
        //   {
        //     UniqueId: "D-123453467810",
        //   },
        //   {
        //     UniqueId: "D-1234567834101",
        //   },
        //   {
        //     UniqueId: "D-1234534678102",
        //   },
        //   {
        //     UniqueId: "D-1234345678103",
        //   },
        //   {
        //     UniqueId: "D-1234567348104",
        //   },
        //   {
        //     UniqueId: "D-1234563478105",
        //   },
        //   {
        //     UniqueId: "D-1233445678106",
        //   },
        // ]
        return {
          options: data.map((item: any) => ({
            label: item.UniqueId,
            value: item.UniqueId,
          })),
          hasMore,
          additional: {
            page: page + 1,
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

  const getDroneByUniqueId = async (uniqueId: string) => {
    try {
      const response = await API.get(endpoint.getDrones, {
        params: {
          search_field: uniqueId,
        },
      });
      const drone = response?.data?.drones?.[0];
      return {
        success: true,
        data: drone,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message ||
          'Error getting drone by unique id',
        data: {
          data: [],
        },
      };
    }
  };

  const getDetailOrder = async ({
    id,
    edit,
  }: {
    id: number;
    edit: boolean;
  }) => {
    try {
      const response = await API.get(endpoint.detailOrder(id));

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
    }
  };

  const getListDeviceTemplate = ({
    key = 'name',
    value = 'id',
  }: { key?: string; value?: string } = {}) => {
    return async (
      search: string,
      loadedOptions: any[],
      { page }: { page: number } = { page: 1 },
    ) => {
      try {
        const response = await API.get(endpoint.library, {
          params: {
            current_page: page,
            page_size: 10,
            name: search,
            active: true,
          },
        });
        const data = response.data || [];
        const hasMore = data.length === 10;
        return {
          options: data.map((item: any) => {
            return {
              label: item.name,
              value: item.id,
            };
          }),
          hasMore,
          additional: {
            page: page + 1,
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
  const getDataDeviceTemplateById = async (deviceId: number) => {
    try {
      const response = await API.get(endpoint.libraryDetail(deviceId), {
        params: {
          id: deviceId,
          edit: true,
          depth: 2,
        },
      });
      // const drone = response?.data?.drones?.[0];
      return {
        success: true,
        data: response?.data,
        message: 'Success',
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message ||
          'Error getting drone by unique id',
        data: {
          data: [],
        },
      };
    }
  };

  const getListTerminalsOptions = () => {
    return async (
      search: string,
      loadedOptions: any,
      { page }: { page: number },
    ) => {
      const response = await API.get(endpoint.hubs, {
        params: {
          name: search,
          current_page: page ?? 1,
          page_size: 10,
          active: true,
        },
      });

      const data = response.data || [];
      const hasMore = response.current_page < response.total_pages;

      return {
        options: data
          .map((item: any) => {
            return { label: item.name, value: item.id };
          })
          .filter(Boolean),
        hasMore,
        additional: {
          page: (page ?? 1) + 1,
        },
      };
    };
  };

  const activeDevice = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.activeDevice(ids));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message || 'Error activating device',
      };
    } finally {
      useLoading && hideLoading();
    }
  };

  const deactiveDevice = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.deactiveDevice(ids));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message:
          (error as any)?.response?.data?.message ||
          'Error deactivating device',
      };
    } finally {
      useLoading && hideLoading();
    }
  };

  return {
    getDeviceManagement,
    actionDevice,
    deleteDevices,
    getDetailOrder,
    createDevice,
    updateDevice,
    getDrones,
    getDroneByUniqueId,
    getDetailDevice,
    getListDeviceTemplate,
    getDataDeviceTemplateById,
    getListTerminalsOptions,
    changeStatusDevice,
    activeDevice,
    deactiveDevice,
  };
};

export default useAPI;
