import { useCallback } from 'react';
import { ToastTopHelper } from 'rj-core';

import { Package, OrderRow } from '../types';
import { CrossOrderPackage } from './useCrossOrderState';

interface UsePackageManagementProps {
  fetchPackageOfOrder: (params: {
    page: number;
    page_size: number;
    operation_id: number;
  }) => Promise<any>;
}

export const usePackageManagement = ({
  fetchPackageOfOrder,
}: UsePackageManagementProps) => {
  // Load packages for a single order
  const loadPackagesForOrder = useCallback(
    async (orderId: number): Promise<Package[]> => {
      try {
        const response = await fetchPackageOfOrder({
          page: 1,
          page_size: 50,
          operation_id: orderId,
        });

        if (response?.data) {
          const formatListPackage = response.data.map((item: any) => ({
            id: item?.order_package_id || item?.id,
            weight: item?.order_item__weight?.value || 0,
            weightUnit: item?.order_item__weight?.unit || 'kg',
            order_id: item?.order_id,
          }));

          return formatListPackage;
        }

        return [];
      } catch (error) {
        console.error('Error loading packages for order:', orderId, error);
        ToastTopHelper.error('Failed to load packages');
        return [];
      }
    },
    [fetchPackageOfOrder],
  );

  // Load packages for all orders in a route group
  const loadPackagesForRouteGroup = useCallback(
    async (orders: OrderRow[]): Promise<CrossOrderPackage[]> => {
      try {
        const allPackages: CrossOrderPackage[] = [];

        for (const order of orders) {
          const response = await fetchPackageOfOrder({
            page: 1,
            page_size: 50,
            operation_id: order.id,
          });

          if (response?.data) {
            const formatListPackage = response.data.map((item: any) => ({
              id: item?.order_package_id || item?.id,
              weight: item?.order_item__weight?.value || 0,
              weightUnit: item?.order_item__weight?.unit || 'kg',
              order_id: order.order_id,
              orderId: order.id,
              orderDetails: order,
            }));
            allPackages.push(...formatListPackage);
          }
        }

        return allPackages;
      } catch (error) {
        console.error('Error loading packages for route group:', error);
        ToastTopHelper.error('Failed to load packages for route group');
        return [];
      }
    },
    [fetchPackageOfOrder],
  );

  return {
    loadPackagesForOrder,
    loadPackagesForRouteGroup,
  };
};
