import { useCallback, useState } from 'react';

import { OrderRow } from '../types';

// Cross-order interfaces
export interface CrossOrderPackage {
  id: string;
  weight?: number;
  weightUnit?: string;
  order_id?: string;
  orderId: number;
  orderDetails: OrderRow;
}

export interface DroneAssignment {
  droneId: string;
  packages: CrossOrderPackage[];
  totalWeight: number;
  availableCapacity: number;
  orders: Set<number>;
}

export interface RouteGroup {
  routeKey: string;
  orders: OrderRow[];
  allPackages: CrossOrderPackage[];
  droneAssignments: Record<string, DroneAssignment>;
  isComplete: boolean;
}

export interface CrossOrderState {
  routeGroups: Record<string, RouteGroup>;
  globalDroneAssignments: Record<string, DroneAssignment>;
}

export const useCrossOrderState = () => {
  const [crossOrderState, setCrossOrderState] = useState<CrossOrderState>({
    routeGroups: {},
    globalDroneAssignments: {},
  });

  // Helper function to generate route key
  const generateRouteKey = useCallback((order: OrderRow): string => {
    return `${order.origin}-${order.destination}`;
  }, []);

  // Helper function to create RouteGroup
  const createRouteGroup = useCallback(
    (routeKey: string, orders: OrderRow[]): RouteGroup => {
      return {
        routeKey,
        orders,
        allPackages: [],
        droneAssignments: {},
        isComplete: false,
      };
    },
    [],
  );

  // Check if two orders have the same route
  const hasSameRoute = useCallback(
    (order1: OrderRow, order2: OrderRow): boolean => {
      return (
        order1.origin === order2.origin &&
        order1.destination === order2.destination
      );
    },
    [],
  );

  // Update route group
  const updateRouteGroup = useCallback(
    (routeKey: string, updater: (group: RouteGroup) => RouteGroup) => {
      setCrossOrderState((prev) => ({
        ...prev,
        routeGroups: {
          ...prev.routeGroups,
          [routeKey]: updater(
            prev.routeGroups[routeKey] || createRouteGroup(routeKey, []),
          ),
        },
      }));
    },
    [createRouteGroup],
  );

  // Get route group
  const getRouteGroup = useCallback(
    (routeKey: string): RouteGroup | undefined => {
      return crossOrderState.routeGroups[routeKey];
    },
    [crossOrderState.routeGroups],
  );

  // Initialize route group for orders
  const initializeRouteGroup = useCallback(
    (currentOrder: OrderRow, allOrders: OrderRow[]) => {
      const routeKey = generateRouteKey(currentOrder);
      const sameRouteOrders = [
        currentOrder,
        ...allOrders.filter(
          (order) =>
            order.id !== currentOrder.id && hasSameRoute(currentOrder, order),
        ),
      ];

      setCrossOrderState((prev) => ({
        ...prev,
        routeGroups: {
          ...prev.routeGroups,
          [routeKey]: createRouteGroup(routeKey, sameRouteOrders),
        },
      }));

      return routeKey;
    },
    [generateRouteKey, hasSameRoute, createRouteGroup],
  );

  return {
    crossOrderState,
    setCrossOrderState,
    generateRouteKey,
    createRouteGroup,
    hasSameRoute,
    updateRouteGroup,
    getRouteGroup,
    initializeRouteGroup,
  };
};
