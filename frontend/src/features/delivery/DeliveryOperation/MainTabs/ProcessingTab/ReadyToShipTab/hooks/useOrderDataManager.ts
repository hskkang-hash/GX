import { useCallback, useEffect, useState } from 'react';
import { ToastTopHelper } from 'rj-core';

import { Drone, Package, OrderRow } from '../types';
import { useCrossOrderState } from './useCrossOrderState';
import { useDroneAssignments } from './useDroneAssignments';
import { useOrderDataFlow } from './useOrderDataFlow';

interface UseOrderDataManagerProps {
  currentOrderDetails: OrderRow | null;
  selectedDroneIds: Record<string, string>;
  onDroneLocationChange?: (
    location: { lat: number; lng: number } | null,
  ) => void;
  onDroneAssignment?: (packageId: string, droneId: string) => void;
}

export const useOrderDataManager = ({
  currentOrderDetails,
  selectedDroneIds,
  onDroneLocationChange,
  onDroneAssignment,
}: UseOrderDataManagerProps) => {
  const [selectedPackageIdx, setSelectedPackageIdx] = useState<string | null>(
    null,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Cross-order state management
  const {
    crossOrderState,
    generateRouteKey,
    hasSameRoute,
    getRouteGroup,
    updateRouteGroup,
  } = useCrossOrderState();

  // Data flow management
  const {
    isLoading,
    isLoadingDrones,
    error,
    routes,
    packages,
    drones,
    selectedRouteId,
    loadOrderData,
    loadDronesForPackage,
    updateSelectedRoute,
    clearData,
  } = useOrderDataFlow();

  // Drone assignment management
  const { globalDroneAssignments, optimizeDroneAssignments, getDroneStatus } =
    useDroneAssignments(
      selectedDroneIds,
      packages,
      drones,
      currentOrderDetails,
      crossOrderState,
      generateRouteKey,
      updateRouteGroup,
    );

  // Auto-select best drone for a package
  const autoSelectBestDrone = useCallback(
    (packageId: string, availableDrones: Drone[]) => {
      if (!currentOrderDetails) return null;

      const selectedPackage = packages.find((p) => p.id === packageId);
      if (!selectedPackage) {
        return null;
      }

      if (!availableDrones.length) {
        return null;
      }

      const packageWeight = selectedPackage.weight || 0;

      // Get drones with capacity analysis using availablePayload
      const dronesWithCapacity = availableDrones.map((drone) => {
        // Use availablePayload for calculations instead of maxLoadValue
        const remainingCapacity = drone.availablePayload; // This is the actual available capacity
        const canFit = remainingCapacity >= packageWeight;

        return {
          ...drone,
          canFit,
          remainingCapacity,
          isOverweight: !canFit,
          efficiency:
            remainingCapacity > 0 ? packageWeight / remainingCapacity : 0,
        };
      });

      // Find best drone (can fit + best efficiency)
      const eligibleDrones = dronesWithCapacity.filter(
        (drone) => drone.canFit && !drone.isOverweight,
      );

      if (eligibleDrones.length === 0) {
        // Don't auto-assign overweight packages - let user manually select if needed
        return null;
      }

      // Sort by efficiency (prefer drones where package uses more of available capacity)
      const bestDrone = eligibleDrones.sort((a, b) => {
        // Primary: Higher efficiency (better space utilization)
        if (b.efficiency !== a.efficiency) return b.efficiency - a.efficiency;
        // Secondary: Smaller remaining capacity after assignment
        const aRemainingAfter = a.remainingCapacity - packageWeight;
        const bRemainingAfter = b.remainingCapacity - packageWeight;
        return aRemainingAfter - bRemainingAfter;
      })[0];

      return bestDrone.doneId;
    },
    [packages, currentOrderDetails],
  );

  // Handle package selection
  const handlePackageSelection = useCallback(
    async (
      packageId: string,
      specificPackages?: Package[],
      explicitRouteId?: number,
    ) => {
      // Use explicit route ID if provided, otherwise use current state
      const routeIdToUse = explicitRouteId || selectedRouteId;

      setSelectedPackageIdx(packageId);

      // Clear drone location when switching packages
      onDroneLocationChange?.(null);

      // ALWAYS load fresh drones for the selected package
      if (routeIdToUse) {
        const loadedDrones = await loadDronesForPackage(
          packageId,
          routeIdToUse,
        );

        // Check if package already has assignment after loading drones
        if (currentOrderDetails) {
          const routeKey = generateRouteKey(currentOrderDetails);
          const routeGroup = getRouteGroup(routeKey);

          if (routeGroup?.droneAssignments) {
            // Find existing assignment for this package
            const existingAssignment = Object.values(
              routeGroup.droneAssignments,
            ).find((assignment) =>
              assignment.packages.some((pkg) => pkg.id === packageId),
            );

            if (existingAssignment) {
              // Update drone location if available
              const assignedDrone = loadedDrones.find(
                (d) => d.doneId === existingAssignment.droneId,
              );
              if (assignedDrone?.droneLocation) {
                onDroneLocationChange?.(assignedDrone.droneLocation);
              }
              return;
            }
          }
        }
      }
    },
    [
      currentOrderDetails,
      generateRouteKey,
      getRouteGroup,
      selectedRouteId,
      loadDronesForPackage,
      onDroneLocationChange,
    ],
  );

  // Handle order selection
  const handleOrderSelection = useCallback(
    async (order: OrderRow) => {
      try {
        // Check if it's the same route as current order
        if (currentOrderDetails && hasSameRoute(currentOrderDetails, order)) {
          // Handle same route logic - preserve existing assignments
          const routeKey = generateRouteKey(order);
          const currentRouteGroup = getRouteGroup(routeKey);
          const existingAssignments = currentRouteGroup?.droneAssignments || {};

          // Extract assignments for this specific order
          const orderAssignments: Record<string, string> = {};
          Object.values(existingAssignments).forEach((assignment) => {
            assignment.packages
              .filter((pkg) => Number(pkg.orderId) === Number(order.id))
              .forEach((pkg) => {
                orderAssignments[pkg.id] = assignment.droneId;
              });
          });

          // Load order data and restore assignments
          const { packages: orderPackages, selectedRouteId: newRouteId } =
            await loadOrderData(order.id);

          // Select first package if available and trigger package selection logic
          if (orderPackages.length > 0) {
            const firstPackageId = orderPackages[0].id;
            setSelectedPackageIdx(firstPackageId);

            // Trigger package selection logic to load drones and auto-select
            // Use a small delay to ensure state updates are complete
            setTimeout(() => {
              handlePackageSelection(firstPackageId, orderPackages, newRouteId);
            }, 50);
          }

          return { preservedAssignments: orderAssignments };
        } else {
          // Different route - fresh start
          clearData();
          setSelectedPackageIdx(null);

          const result = await loadOrderData(order.id);

          // Select first package if available and trigger drone loading
          if (result.packages.length > 0) {
            const firstPackageId = result.packages[0].id;
            setSelectedPackageIdx(firstPackageId);

            // Trigger package selection logic to load drones and auto-select
            // Use a small delay to ensure state updates are complete
            setTimeout(() => {
              handlePackageSelection(
                firstPackageId,
                result.packages,
                result.selectedRouteId,
              );
            }, 50);
          }

          return result;
        }
      } catch (error) {
        ToastTopHelper.error('Failed to load order data');
      }
    },
    [
      currentOrderDetails,
      hasSameRoute,
      generateRouteKey,
      getRouteGroup,
      loadOrderData,
      clearData,
      handlePackageSelection,
    ],
  );

  // Handle route selection
  const handleRouteSelection = useCallback(
    async (routeId: number) => {
      // Update route state first
      updateSelectedRoute(routeId);

      // ALWAYS reload fresh drones for current package with new route ID
      if (selectedPackageIdx) {
        // Use explicit route ID to avoid any race conditions
        await handlePackageSelection(selectedPackageIdx, packages, routeId);
      }
    },
    [updateSelectedRoute, selectedPackageIdx, packages, handlePackageSelection],
  );

  // Get cross-order status
  const getCrossOrderStatus = useCallback(() => {
    if (!currentOrderDetails) return null;

    const routeKey = generateRouteKey(currentOrderDetails);
    const routeGroup = getRouteGroup(routeKey);

    if (!routeGroup) return null;

    const totalOrders = routeGroup.orders.length;
    const completedOrders = new Set<number>();
    const incompleteOrders = new Set<number>();

    // Check completion status for each order
    routeGroup.orders.forEach((order) => {
      const orderPackages = routeGroup.allPackages.filter(
        (pkg) => pkg.orderId === order.id,
      );
      const assignedPackages = orderPackages.filter((pkg) =>
        Object.values(routeGroup.droneAssignments || {}).some((drone) =>
          drone.packages.some((p) => p.id === pkg.id),
        ),
      );

      if (
        assignedPackages.length === orderPackages.length &&
        orderPackages.length > 0
      ) {
        completedOrders.add(order.id);
      } else if (assignedPackages.length > 0) {
        incompleteOrders.add(order.id);
      }
    });

    return {
      totalOrders,
      completedOrders: completedOrders.size,
      incompleteOrders: incompleteOrders.size,
      routeGroup,
    };
  }, [currentOrderDetails, generateRouteKey, getRouteGroup]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      clearData();
    };
  }, [clearData]);

  return {
    // State
    isLoading,
    isLoadingDrones,
    error,
    routes,
    packages,
    drones,
    selectedRouteId,
    selectedPackageIdx,
    isSubmitting,

    // Cross-order state
    crossOrderState,
    globalDroneAssignments,

    // Actions
    handleOrderSelection,
    handlePackageSelection,
    handleRouteSelection,
    setSelectedPackageIdx,
    setIsSubmitting,

    // Utilities
    autoSelectBestDrone,
    getDroneStatus,
    getCrossOrderStatus,
    optimizeDroneAssignments,
    generateRouteKey,
    getRouteGroup,
    updateRouteGroup,
    hasSameRoute,
  };
};
