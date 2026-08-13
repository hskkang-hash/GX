import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';

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

const useAPI = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const getListTerminalsAPI = async ({
    pageSize,
    currentPage,
    objSearch,
    active,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject;
    active?: boolean;
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

      const response = await API.get(endpoint.terminals, {
        params: paramsFetch,
      });

      return {
        data: response.data,
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch (error) {
      console.error('Error fetching terminals:', error);
      return { data: [], totalPage: 0, totalItem: 0 };
    } finally {
      hideLoading();
    }
  };

  const createTerminalAPI = async (data: {
    name: string;
    terminal_type_ids: number[];
    function_ids: number[];
    postal_code: string;
    time_stops: string;
    latitude: number;
    longitude: number;
    city_province: string;
    city_county_district: string;
    ward_town_township: string;
    street_address: string;
    full_address: string;
    address_note: string;
    manager_name: string;
    manufacturer: string;
    year_of_manufacture: string;
    url: string;
    note: string;
    avatar: any;
  }) => {
    try {
      showLoading();
      const formData = new FormData();

      const { avatar, ...restData } = data;
      formData.append('data', JSON.stringify(restData));
      if (avatar) {
        formData.append('avatar', avatar);
      }
      const response = await API.post(endpoint.terminals, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return {
        success: true,
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

  const getDetailTerminalAPI = async (id: number) => {
    try {
      showLoading();
      const response = await API.get(endpoint.terminals + `/${id}`);
      if (response.success) {
        return {
          success: true,
          message: response.message,
          data: response.data,
        };
      }
      return {
        success: false,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      hideLoading();
    }
  };




  const getOperatingTimeTerminalAPI = async (id: number) => {
    try {
      showLoading();
      const response = await API.get(endpoint.terminalsOperatingTime(id));
      return {
        success: true,
        message: response.message,
        data: response.data,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
        data: [],
      };
    } finally {
      hideLoading();
    }
  };

  const updateTerminalAPI = async (
    id: number,
    data: {
      name: string;
      terminal_type_ids: number[];
      function_ids: number[];
      postal_code: string;
      time_stops: string;
      latitude: number;
      longitude: number;
      city_province: string;
      city_county_district: string;
      ward_town_township: string;
      street_address: string;
      full_address: string;
      address_note: string;
      manager_name: string;
      manufacturer: string;
      year_of_manufacture: string;
      url: string;
      note: string;
      avatar: any;
    },
  ) => {
    try {
      showLoading();
      const formData = new FormData();
      const { avatar, ...restData } = data;
      formData.append('data', JSON.stringify(restData));
      if (avatar) {
        formData.append('avatar', avatar);
      }
      const response = await API.put(endpoint.terminals + `/${id}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
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

  const activeDeactiveTerminalAPI = async (ids: string, useLoading = false) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.changeStatusTerminal(ids));
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
      useLoading && hideLoading();
    }
  };

  const getListDockingStation = async ({
    pageSize,
    currentPage,
    objSearch,
    active,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject;
    active?: boolean;
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

      const response = await API.get(endpoint.dockingStation, {
        params: paramsFetch,
      });

      return {
        data: response.data,
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch (error) {
      console.error('Error fetching terminals:', error);
      return { data: [], totalPage: 0, totalItem: 0 };
    } finally {
      hideLoading();
    }
  };

  const getListGroup = () => {
    return async (
      search: string,
      loadedOptions: any,
      { page }: { page: number },
    ) => {
      const response = await API.get(endpoint.groups, {
        params: {
          name: search,
          current_page: page ?? 1,
          page_size: 10,
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

  const activeTerminalAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.activeTerminal(ids));
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
      useLoading && hideLoading();
    }
  };

  const deactiveTerminalAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.deactiveTerminal(ids));
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
      useLoading && hideLoading();
    }
  };

  return {
    getListTerminalsAPI,
    createTerminalAPI,
    getDetailTerminalAPI,
    updateTerminalAPI,
    activeDeactiveTerminalAPI,
    getListDockingStation,
    getListGroup,

    activeTerminalAPI,
    deactiveTerminalAPI,
    getOperatingTimeTerminalAPI
  };
};

export default useAPI;
