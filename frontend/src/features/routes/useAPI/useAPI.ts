import { useLoadingContext } from 'rj-core';

import { SelectOption } from '../../../components/selects/CustomSelect';
import API, { endpoint } from '../../../services/API';

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

export type Command = {
  id: string;
  name: string;
  key: string;
  value: string;
};

export type Terminal = {
  terminal_id: number;
  stop: boolean;
  order: number;
  latitude?: string;
  longitude?: string;
  for_robot?: boolean;
  is_temp?: boolean;
  name?: string;
  cruise_speed?: string;
  operating_altitude?: string;
  command?: Command[];
};

export type FormDataSubmitRoute = {
  name: string;
  code: string;
  note?: string;
  total_distance: string;
  estimated_time: string;
  total_stops: number | null;
  terminals: Terminal[];
  two_way: boolean;
  group: SelectOption | null;
  service?: SelectOption | null;
};

const useAPI = () => {
  const { showLoading, hideLoading } = useLoadingContext();

  const getListRoutesAPI = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject;
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

      const response = await API.get(endpoint.routes, {
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

  const addNewRouteAPI = async (data: FormDataSubmit) => {
    try {
      showLoading();
      const response = await API.post(endpoint.routes, data, {
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

  const getDetailRouteAPI = async (id: number) => {
    try {
      showLoading();
      const response = await API.get(endpoint.routes + `/${id}`);

      console.log('response_getDetailRouteAPI', response.data);
      return {
        success: response.success,
        data: response.data,
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

  const updateRouteAPI = async (id: number, data: FormDataSubmit) => {
    try {
      showLoading();
      const response = await API.put(endpoint.routes + `/${id}`, data, {
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

  const changeStatusRouteAPI = async (ids: string) => {
    try {
      showLoading();
      const response = await API.put(endpoint.changeStatusRoute(ids));

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

  const activeRouteAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.activeRoute(ids));
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

  const deactiveRouteAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.deactiveRoute(ids));
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
    getListRoutesAPI,
    addNewRouteAPI,
    getDetailRouteAPI,
    updateRouteAPI,
    changeStatusRouteAPI,

    activeRouteAPI,
    deactiveRouteAPI,
  };
};

export default useAPI;
