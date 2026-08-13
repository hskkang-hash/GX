import { useCallback, useRef, useState } from 'react';
import { ToastTopHelper } from 'rj-core';

import { useOperationOrder } from '../../../../hooks/useOperationOrder';
import { Drone, Package, OrderRow } from '../types';

interface UseOrderDataFlowProps {
  onRouteChange?: (routeId: number | null) => void;
  onPackagesChange?: (packages: Package[]) => void;
  onDronesChange?: (drones: Drone[]) => void;
}

interface DataFlowState {
  isLoading: boolean;
  isLoadingDrones: boolean;
  error: string | null;
  routes: any[];
  packages: Package[];
  drones: Drone[];
  selectedRouteId: number | null;
  hasMoreRoutes: boolean;
  hasMoreDrones: boolean;
}

export const useOrderDataFlow = ({
  onRouteChange,
  onPackagesChange,
  onDronesChange,
}: UseOrderDataFlowProps = {}) => {
  const {
    fetchRouteSelect,
    fetchPackageOfOrder,
    fetchDronesByPackageAndRoute,
  } = useOperationOrder();

  const [state, setState] = useState<DataFlowState>({
    isLoading: false,
    isLoadingDrones: false,
    error: null,
    routes: [],
    packages: [],
    drones: [],
    selectedRouteId: null,
    hasMoreRoutes: true,
    hasMoreDrones: true,
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const droneCache = useRef<Record<string, Drone[]>>({});

  // Helper function to update state
  const updateState = useCallback((updates: Partial<DataFlowState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  // Cancel any ongoing requests
  const cancelRequests = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
  }, []);

  // Clear all data
  const clearData = useCallback(() => {
    updateState({
      routes: [],
      packages: [],
      drones: [],
      selectedRouteId: null,
      error: null,
      hasMoreRoutes: true,
      hasMoreDrones: true,
    });
    droneCache.current = {};
  }, [updateState]);

  // Load routes for an order
  const loadRoutes = useCallback(
    async (orderId: number) => {
      try {
        updateState({ isLoading: true, error: null });

        const response = await fetchRouteSelect({
          page: 1,
          operation_id: orderId,
        });

        if (response?.data) {
          const formattedRoutes = response.data.map((item: any) => ({
            id: item?.id,
            route_name: item?.name,
            route_description: item?.full_description,
            route_distance: item?.total_distance,
            route_duration: item?.estimated_time,
            routes: item?.full_description,
          }));

          updateState({
            routes: formattedRoutes,
            hasMoreRoutes: response.hasMore || false,
          });

          // Auto-select first route
          if (formattedRoutes.length > 0) {
            const firstRouteId = formattedRoutes[0].id;
            updateState({ selectedRouteId: firstRouteId });
            onRouteChange?.(firstRouteId);
            return firstRouteId;
          } else {
            console.warn('No routes found in response data');
          }
        } else {
          console.warn('No response data received for routes');
          updateState({ routes: [] });
        }
      } catch (error) {
        console.error('Error loading routes:', error);
        updateState({ error: 'Failed to load routes' });
        ToastTopHelper.error('Failed to load routes');
      } finally {
        updateState({ isLoading: false });
      }
      return null;
    },
    [fetchRouteSelect, updateState, onRouteChange],
  );

  // Load packages for an order
  const loadPackages = useCallback(
    async (orderId: number) => {
      try {
        updateState({ isLoading: true, error: null });

        const response = await fetchPackageOfOrder({
          page: 1,
          page_size: 50,
          operation_id: orderId,
        });

        if (response?.data) {
          const formattedPackages = response.data.map((item: any) => ({
            id: item?.order_package_id || item?.id,
            weight: item?.order_item__weight?.value || 0,
            weightUnit: item?.order_item__weight?.unit || 'kg',
            order_id: item?.order_id,
          }));

          updateState({ packages: formattedPackages });
          onPackagesChange?.(formattedPackages);
          return formattedPackages;
        }
      } catch (error) {
        console.error('Error loading packages:', error);
        updateState({ error: 'Failed to load packages' });
        ToastTopHelper.error('Failed to load packages');
      } finally {
        updateState({ isLoading: false });
      }
      return [];
    },
    [fetchPackageOfOrder, updateState, onPackagesChange],
  );

  // Load drones - always fetch fresh data
  const loadDrones = useCallback(
    async (packageId: string, routeId: number, forceRefresh = true) => {
      try {
        updateState({ isLoadingDrones: true, error: null });

        const cacheKey = `${packageId}-${routeId}`;
        console.log(
          `🚁 Always fetching fresh drones for package: ${packageId}, route: ${routeId}`,
        );

        // Clear cache for this key to ensure fresh fetch
        if (forceRefresh && droneCache.current[cacheKey]) {
          delete droneCache.current[cacheKey];
        }

        console.log(
          `📡 API Call: fetchDronesByPackageAndRoute with packageId=${packageId}, routeId=${routeId}`,
        );
        const response = await fetchDronesByPackageAndRoute({
          page: 1,
          page_size: 20,
          operation_item_id: Number(packageId),
          route_id: routeId,
        });

        if (response?.data) {
          const formattedDrones = response.data.map((item: any) => {
            const maxLoadValue = parseFloat(
              item?.weight_capacity?.value || '0',
            );
            const maxLoadUnit = item?.weight_capacity?.unit || 'kg';
            const availablePayload = parseFloat(item?.available_payload || '0');
            const batteryValue = item?.battery_capacity?.value || 0;
            const batteryUnit = item?.battery_capacity?.unit || 'mAh';

            return {
              doneId: item?.id,
              id: item?.serial_number || item?.name,
              name: item?.name,
              model: item?.main_type__name || item?.library__name || '',
              battery: `${batteryValue} ${batteryUnit}`,
              maxLoad: `${maxLoadValue} ${maxLoadUnit}`,
              maxLoadValue,
              maxLoadUnit,
              availablePayload, // Add the available payload field
              droneLocation:
                item?.terminal__latitude && item?.terminal__longitude
                  ? {
                      lat: parseFloat(item.terminal__latitude),
                      lng: parseFloat(item.terminal__longitude),
                    }
                  : null,
              currentLoad: 0,
              assignedPackages: [],
              disabled: item?.disable || false,
              disableReason: item?.reason || null,
            };
          });

          // Cache the results
          droneCache.current[cacheKey] = formattedDrones;

          updateState({
            drones: formattedDrones,
            hasMoreDrones: response.hasMore || false,
          });

          onDronesChange?.(formattedDrones);
          return formattedDrones;
        }
      } catch (error) {
        console.error('Error loading drones:', error);
        updateState({ error: 'Failed to load drones' });
        ToastTopHelper.error('Failed to load drones');
      } finally {
        updateState({ isLoadingDrones: false });
      }
      return [];
    },
    [fetchDronesByPackageAndRoute, updateState, onDronesChange],
  );

  // Complete data flow for an order
  const loadOrderData = useCallback(
    async (orderId: number, packageId?: string) => {
      console.log('🔄 Starting complete data flow for order:', orderId);

      try {
        cancelRequests();
        clearData();
        updateState({ isLoading: true });

        // Step 1: Load routes
        console.log('📡 Step 1: Loading routes...');
        const selectedRouteId = await loadRoutes(orderId);

        if (!selectedRouteId) {
          console.warn('No routes available for order:', orderId);
          updateState({ error: null }); // Clear any route loading errors
          return {
            packages: [],
            drones: [],
            routes: [],
            selectedRouteId: null,
          };
        }

        // Step 2: Load packages
        console.log('📦 Step 2: Loading packages...');
        const packages = await loadPackages(orderId);

        if (packages.length === 0) {
          console.warn('No packages found for order:', orderId);
          return { packages: [], drones: [], selectedRouteId };
        }

        // Step 3: Don't load drones here - let handlePackageSelection handle it to avoid duplicate calls
        console.log(
          '🚁 Step 3: Skipping drone loading in loadOrderData to prevent duplicates',
        );

        return { packages, drones: [], selectedRouteId };
      } catch (error) {
        console.error('Error in complete data flow:', error);
        updateState({ error: 'Failed to load order data' });
        return { packages: [], drones: [], routes: [], selectedRouteId: null };
      } finally {
        updateState({ isLoading: false });
      }
    },
    [
      cancelRequests,
      clearData,
      loadRoutes,
      loadPackages,
      loadDrones,
      updateState,
    ],
  );

  // Load drones for a specific package (always fetch fresh)
  const loadDronesForPackage = useCallback(
    async (packageId: string, routeId?: number) => {
      // Use provided routeId or current selected route
      const targetRouteId = routeId || state.selectedRouteId;

      if (!targetRouteId) {
        console.warn('Cannot load drones: no route selected');
        return [];
      }

      console.log(
        `🚁 ALWAYS Loading fresh drones for package ${packageId} with route ${targetRouteId}`,
      );
      return loadDrones(packageId, targetRouteId, true); // Always force refresh
    },
    [state.selectedRouteId, loadDrones],
  );

  // Clear cache for a specific key or all cache
  const clearCache = useCallback((cacheKey?: string) => {
    if (cacheKey) {
      delete droneCache.current[cacheKey];
    } else {
      droneCache.current = {};
    }
  }, []);

  // Cleanup function
  const cleanup = useCallback(() => {
    cancelRequests();
    clearData();
    clearCache();
  }, [cancelRequests, clearData, clearCache]);

  return {
    // State
    ...state,

    // Actions
    loadOrderData,
    loadRoutes,
    loadPackages,
    loadDrones,
    loadDronesForPackage,
    clearData,
    clearCache,
    cleanup,

    // Utilities
    updateSelectedRoute: (routeId: number | null) => {
      updateState({ selectedRouteId: routeId });
      onRouteChange?.(routeId);
    },
  };
};
