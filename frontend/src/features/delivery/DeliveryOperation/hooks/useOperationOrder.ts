import qs from 'qs';
import { useTranslation } from 'react-i18next';
import { ToastTopHelper, useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';

import { DroneSensorStatusType } from '../MainTabs/ProcessingTab/components/DroneSensorStatus';

// Define interface for the search object
interface SearchParam {
  id: string;
  value: string | number | boolean;
}

// Define interface for sort params
interface SortParam {
  id: string;
  desc: boolean;
}

interface SearchObject {
  searchParams?: SearchParam[];
  filters?: Record<string, unknown>;
  sortParams?: SortParam[];
  status_codes?: Array<string>;
}

export const useOperationOrder = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const { i18n } = useTranslation();

  const fetchOperationOrder = async ({
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
      const paramsFetch: Record<string, any> = {
        page_size: pageSize,
        current_page: currentPage,
      };

      if (objSearch) {
        if (objSearch.status_codes) {
          paramsFetch.status_codes = objSearch.status_codes;
        }

        if (objSearch.searchParams) {
          objSearch.searchParams.forEach((item: SearchParam) => {
            paramsFetch[item.id] = item.value;
          });
        }

        if (objSearch.filters) {
          paramsFetch.filters = objSearch.filters;
        }

        if (objSearch.sortParams?.length) {
          paramsFetch.sort_obj = objSearch.sortParams;
        }
      }

      const response = await API.get(endpoint.operationOrder, {
        params: paramsFetch,
        paramsSerializer: (params) =>
          qs.stringify(params, { arrayFormat: 'repeat' }),
      });

      return {
        data: response.data,
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch (err) {
      return {
        data: [],
        totalPage: 0,
        totalItem: 0,
      };
    } finally {
      hideLoading();
    }
  };

  const fetchTransitOrder = async ({
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
      const paramsFetch: Record<string, any> = {
        page_size: pageSize,
        current_page: currentPage,
      };

      if (objSearch) {
        if (objSearch.status_codes) {
          paramsFetch.status_codes = objSearch.status_codes;
        }

        if (objSearch.searchParams) {
          objSearch.searchParams.forEach((item: SearchParam) => {
            paramsFetch[item.id] = item.value;
          });
        }

        if (objSearch.filters) {
          paramsFetch.filters = objSearch.filters;
        }

        if (objSearch.sortParams?.length) {
          paramsFetch.sort_obj = objSearch.sortParams;
        }
      }

      const response = await API.get(endpoint.transit, {
        params: paramsFetch,
      });

      return {
        data: response.data?.map((item: any) => ({
          ...item,
          delivery_device: Array.isArray(item?.delivery_device)
            ? item.delivery_device
                .filter(
                  (drone: any) =>
                    drone !== null &&
                    drone !== undefined &&
                    typeof drone === 'string' &&
                    drone.trim().length > 0,
                )
                .map((drone: string, index: number) => ({
                  id: drone,
                  index: index + 1,
                  uuid: drone,
                  label: `${item?.device_name[index]} (${drone})`,
                  value: drone,
                }))
            : [],
        })),
        totalPage: response.total_pages,
        totalItem: response.total_items,
      };
    } catch (err) {
      console.log(err);
    } finally {
      hideLoading();
    }
  };

  //pagination  infinite scroll
  const fetchRouteSelect = async ({
    page,
    page_size = 10,
    operation_id,
  }: {
    page: number;
    page_size?: number;
    operation_id: number;
  }) => {
    const response = await API.get(endpoint.routeSelect, {
      params: {
        operation_id: operation_id,
        current_page: page,
        page_size,
      },
    });
    const totalRoutes = response.total_items;
    const hasMore = page * page_size < totalRoutes;

    return {
      data: response.data,
      total: totalRoutes,
      current_page: page,
      page_size,
      hasMore,
    };
  };

  const fetchPackageOfOrder = async ({
    page,
    page_size = 10,
    operation_id,
  }: {
    page: number;
    page_size?: number;
    operation_id: number;
  }) => {
    try {
      const response = await API.get(endpoint.droneSelect(operation_id), {
        params: {
          current_page: page,
          page_size,
        },
      });
      const totalRoutes = response.total_items;
      const hasMore = page * page_size < totalRoutes;

      return {
        data: response.data,
        total: totalRoutes,
        current_page: page,
        page_size,
        hasMore,
      };
    } catch (error) {
      console.log('error fetchPackageOfOrder', error);
      ToastTopHelper.error('Failed to get drones by package');
    }
  };

  const fetchDronesByPackageId = async ({
    page,
    page_size = 10,
    operation_item_id,
  }: {
    page: number;
    page_size?: number;
    operation_item_id: number;
  }) => {
    try {
      const response = await API.get(
        endpoint.dronesByPackageId(operation_item_id),
        {
          params: {
            current_page: page,
            page_size,
          },
        },
      );

      const apiData = Array.isArray(response.data) ? response.data : [];
      const apiTotal =
        typeof response.total_items === 'number'
          ? response.total_items
          : apiData.length;

      const hasMore = page * page_size < apiTotal;

      return {
        data: apiData,
        total: apiTotal,
        current_page: page,
        page_size,
        hasMore,
      };
    } catch (error: any) {
      console.log('Error fetchDronesByPackageId', error);
      ToastTopHelper.error(
        error.response?.data?.message || 'Failed to fetch drones',
      );
    }
  };

  const fetchDronesByPackageAndRoute = async ({
    page,
    page_size = 10,
    operation_item_id,
    route_id,
  }: {
    page: number;
    page_size?: number;
    operation_item_id: number;
    route_id: number;
  }) => {
    try {
      const response = await API.get(
        endpoint.dronesByPackageAndRoute(operation_item_id, route_id),
        {
          params: {
            current_page: page,
            page_size,
          },
        },
      );

      const apiData = Array.isArray(response.data) ? response.data : [];
      const apiTotal =
        typeof response.total_items === 'number'
          ? response.total_items
          : apiData.length;

      const hasMore = page * page_size < apiTotal;

      return {
        data: apiData,
        total: apiTotal,
        current_page: page,
        page_size,
        hasMore,
      };
    } catch (error: any) {
      console.log('Error fetchDronesByPackageId', error);
      ToastTopHelper.error(
        error.response?.data?.message || 'Failed to fetch drones',
      );
    }
  };

  const fetchUpdateProcessing = async ({
    operation_id,
    route_id,
  }: {
    operation_id: number;
    route_id: number;
  }) => {
    try {
      showLoading();
      const response = await API.put(
        endpoint.processing(operation_id, route_id),
        {
          params: {
            operation_id: operation_id,
            route_id: route_id,
          },
        },
      );
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        data: [],
      };
    } finally {
      hideLoading();
    }
  };

  const confirmPackage = async ({ package_id }: { package_id: number }) => {
    try {
      showLoading();
      const response = await API.post(endpoint.confirmPackage(package_id));
      return {
        success: true,
        message: response.message,
      };
    } catch (error) {
      return {
        success: false,
        message: (error as any)?.response?.data?.message,
      };
    } finally {
      hideLoading();
    }
  };

  const fetchDroneStatus = async ({
    drone_uuid,
    monitoring_items,
    time_window_minutes,
  }: {
    drone_uuid: string;
    monitoring_items?: string[];
    time_window_minutes?: number;
  }) => {
    const payload: Record<string, any> = {
      unique_id: drone_uuid,
    };

    if (monitoring_items && monitoring_items.length > 0) {
      payload.monitoring_items = monitoring_items;
    }

    if (time_window_minutes) {
      payload.time_window_minutes = time_window_minutes;
    }

    const response = await API.post(endpoint.droneStatus, payload);

    if (response?.success) {
      const activeDrone = response?.data?.active_drone;
      const allDrones = response?.data?.all_drones || [];

      // Find matching drone in all_drones by comparing unique_id with unit_id
      const matchedDrone = allDrones.find(
        (drone: { unit_id: string }) =>
          drone?.unit_id === activeDrone?.unique_id,
      );

      return {
        success: true,
        data: {
          ...activeDrone,
          color: matchedDrone?.color || '#1F2A80',
        },
      };
    } else {
      return {
        success: false,
        data: null,
      };
    }
  };

  const fetchConfirmDrone = async (
    jsonData: { drone_id: number; package_id: number }[],
  ) => {
    try {
      const response = await API.post(endpoint.confirmDrone, jsonData);
      console.log('response_3434', response);
      return {
        success: true,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message,
      };
    }
  };

  const fetchPackageProcessingStatus = async (operation_item_id: number) => {
    try {
      showLoading();
      const { success, data } = await API.get(
        endpoint.packageProcessingStatus(operation_item_id),
      );
      if (success) {
        return {
          success: true,
          data: data,
        };
      }
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.message,
      };
    } finally {
      hideLoading();
    }
  };
  const actionCancelOrder = async ({
    order_ids,
    reason_note,
  }: {
    order_ids: number[];
    reason_note: string;
  }) => {
    try {
      showLoading();
      const response = await API.post(endpoint.cancelAwaitingOrder, {
        order_ids: order_ids,
        reason_note: reason_note,
      });
      if (response.success) {
        ToastTopHelper.success(response.message);
        return {
          success: true,
          message: response.message,
        };
      } else {
        ToastTopHelper.error(response.message);
        return {
          success: false,
          message: response.message,
        };
      }
    } catch (error: any) {
      ToastTopHelper.error(error.response?.data?.message);
    } finally {
      hideLoading();
    }
  };

  const actionCancelFlight = async ({
    drone_id,
    order_ids,
  }: {
    drone_id: number | null;
    order_ids: number[];
  }) => {
    try {
      showLoading();
      const response = await API.post(endpoint.cancelFlight, {
        drone_id: drone_id,
        order_ids: order_ids,
      });
      if (response.success) {
        ToastTopHelper.success(response.message);
        return {
          success: true,
          message: response.message,
        };
      } else {
        ToastTopHelper.error(response.message);
        return {
          success: false,
          message: response.message,
        };
      }
    } catch (error: any) {
      ToastTopHelper.error(error.response?.data?.message);
    } finally {
      hideLoading();
    }
  };

  const actionChangeDrone = async ({
    order_ids,
    from_drone,
    to_drone,
    route_id,
  }: {
    order_ids: number[];
    from_drone: number | null;
    to_drone?: number | null;
    route_id: number;
  }) => {
    try {
      console.log(
        'actionChangeDrone',
        order_ids,
        from_drone,
        to_drone,
        route_id,
      );
      showLoading();
      const response = await API.post(endpoint.changeDrone, {
        order_ids: order_ids,
        from_drone: from_drone,
        to_drone: to_drone,
        route_id: route_id,
      });
      if (response.success) {
        ToastTopHelper.success(response.message);
        return {
          success: true,
          message: response.message,
        };
      } else {
        ToastTopHelper.error(response.message);
        return {
          success: false,
          message: response.message,
        };
      }
    } catch (error: any) {
      ToastTopHelper.error(error.response?.data?.message);
    } finally {
      hideLoading();
    }
  };

  const actionUploadRoute = async ({
    order_ids,
    drone_unique_id,
  }: {
    order_ids: number[];
    drone_unique_id: string;
  }) => {
    try {
      showLoading();
      const response = await API.post(endpoint.uploadRoute, {
        order_ids: order_ids,
        drone_unique_id: drone_unique_id,
      });
      if (response.success) {
        ToastTopHelper.success(response.message);
        return {
          success: true,
          message: response.message,
        };
      } else {
        ToastTopHelper.error(response.message);
        return {
          success: false,
          message: response.message,
        };
      }
    } catch (error: any) {
      ToastTopHelper.error(error.response?.data?.message);
    } finally {
      hideLoading();
    }
  };

  const actionDeliveryStart = async ({
    order_ids,
    drone_id,
  }: {
    order_ids: number[];
    drone_id: number;
  }) => {
    try {
      showLoading();
      const payload: Record<string, any> = {
        order_ids: order_ids,
        drone_id: drone_id,
      };
      const response = await API.post(endpoint.approveFlight, payload);

      if (response.success) {
        const message =
          response?.data?.message?.en || response?.data?.message?.kr
            ? response?.data?.message[i18n.language === 'en' ? 'en' : 'kr']
            : response.message;
        ToastTopHelper.success(message);
        return {
          success: true,
          message: message,
        };
      } else {
        ToastTopHelper.error(response.message);
        return {
          success: false,
          message: response.message,
        };
      }
    } catch (error: any) {
      ToastTopHelper.error(error.response?.data?.message);
    } finally {
      hideLoading();
    }
  };

  const actionConfirmFlight = async ({
    order_ids,
    check_lists,
    drone_id,
    not_yet,
    auto_checklist,
  }: {
    order_ids: number[];
    check_lists: number[];
    drone_id: number;
    not_yet: boolean;
    auto_checklist: DroneSensorStatusType[];
  }) => {
    try {
      showLoading();
      const payload: Record<string, any> = {
        order_ids: order_ids,
        check_lists: check_lists,
        drone_id: drone_id,
        auto_checklist: auto_checklist,
      };
      if (not_yet) {
        payload.not_yet = not_yet;
      }
      const response = await API.post(endpoint.approveFlight, payload);

      if (response.success) {
        const message =
          response?.data?.message?.en || response?.data?.message?.kr
            ? response?.data?.message[i18n.language === 'en' ? 'en' : 'kr']
            : response.message;
        ToastTopHelper.success(message);
        return {
          success: true,
          message: message,
        };
      } else {
        ToastTopHelper.error(response.message);
        return {
          success: false,
          message: response.message,
        };
      }
    } catch (error: any) {
      ToastTopHelper.error(error.response?.data?.message);
    } finally {
      hideLoading();
    }
  };

  return {
    fetchOperationOrder,
    fetchTransitOrder,
    fetchRouteSelect,
    fetchUpdateProcessing,
    fetchPackageOfOrder,
    confirmPackage,
    fetchDronesByPackageId,
    fetchDronesByPackageAndRoute,
    fetchDroneStatus,
    fetchConfirmDrone,
    fetchPackageProcessingStatus,

    actionCancelOrder,
    actionCancelFlight,
    actionChangeDrone,
    actionUploadRoute,
    actionConfirmFlight,
    actionDeliveryStart,
  };
};
