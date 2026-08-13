import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '../../../../../../../services/API';

export const useReadyToShipTab = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const getDetailOrder = async (id: number) => {
    try {
      showLoading();
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
    } finally {
      hideLoading();
    }
  };
  const cancelOrder = async (listId: number[], reason: string) => {
    try {
      showLoading();
      const response = await API.post(endpoint.cancelAwaitingOrder, {
        order_ids: listId,
        reason_note: reason,
      });
      return {
        success: response.success,
        message: response.message,
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
    getDetailOrder,
    cancelOrder,
  };
};
