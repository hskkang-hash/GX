import { useMemo, useCallback, useEffect } from 'react';

import { Drone, Package, OrderRow } from '../types';
import {
  CrossOrderState,
  CrossOrderPackage,
  DroneAssignment,
} from './useCrossOrderState';

export const useDroneAssignments = (
  selectedDroneIds: Record<string, string>,
  listPackage: Package[],
  drones: Drone[],
  currentOrderDetails: OrderRow | null,
  crossOrderState: CrossOrderState,
  generateRouteKey: (order: OrderRow) => string,
  updateRouteGroup: (routeKey: string, updater: (group: any) => any) => void, // Add this param
) => {
  // 🔄 Update cross-order state when selections change - IMMEDIATE UPDATE
  useEffect(() => {
    console.log('🔄 useEffect triggered - updating cross-order state...', {
      currentOrderDetails: currentOrderDetails?.id,
      selectedDroneIds,
      selectedDroneIdsCount: Object.keys(selectedDroneIds).length,
      hasUpdateFunction: !!updateRouteGroup,
    });

    if (!currentOrderDetails || !updateRouteGroup) {
      console.log('❌ Missing requirements for update:', {
        hasCurrentOrder: !!currentOrderDetails,
        hasUpdateFunction: !!updateRouteGroup,
      });
      return;
    }

    const routeKey = generateRouteKey(currentOrderDetails);
    console.log('🗺️ Updating route group:', routeKey);

    updateRouteGroup(routeKey, (group) => {
      console.log('📝 Current group state before update:', {
        existingAssignments: Object.keys(group.droneAssignments || {}).length,
        currentOrderId: currentOrderDetails.id,
        ordersInGroup: group.orders?.length || 0,
      });

      // Ensure current order is in the route group
      const updatedOrders = [...group.orders];
      const currentOrderExists = updatedOrders.some(
        (order) => order.id === currentOrderDetails.id,
      );
      if (!currentOrderExists) {
        console.log('➕ Adding current order to route group');
        updatedOrders.push(currentOrderDetails);
      }

      const newDroneAssignments = { ...group.droneAssignments };

      // 🎯 FIXED: Only clear assignments from CURRENT ORDER, not all orders
      Object.keys(newDroneAssignments).forEach((droneId) => {
        const beforeLength = newDroneAssignments[droneId].packages.length;

        // Only remove packages from current order
        newDroneAssignments[droneId].packages = newDroneAssignments[
          droneId
        ].packages.filter((pkg) => pkg.orderId !== currentOrderDetails.id);

        const afterLength = newDroneAssignments[droneId].packages.length;
        const removedCount = beforeLength - afterLength;

        if (removedCount > 0) {
          console.log(
            `🧹 Removed ${removedCount} packages from current order ${currentOrderDetails.id} on drone ${droneId}`,
          );
        }

        // Recalculate weight and orders based on remaining packages
        newDroneAssignments[droneId].totalWeight = newDroneAssignments[
          droneId
        ].packages.reduce((sum, pkg) => sum + (pkg.weight || 0), 0);
        newDroneAssignments[droneId].orders = new Set(
          newDroneAssignments[droneId].packages.map((pkg) => pkg.orderId),
        );

        // 🎯 IMPORTANT: Only remove assignment if NO packages left at all
        if (newDroneAssignments[droneId].packages.length === 0) {
          console.log(`🗑️ Removing empty assignment for drone ${droneId}`);
          delete newDroneAssignments[droneId];
        } else {
          // Update available capacity for remaining assignments using availablePayload
          const drone = drones.find((d) => d.doneId === droneId);
          if (drone) {
            // Use availablePayload instead of maxLoadValue for capacity calculations
            const baseCapacity = drone.availablePayload || drone.maxLoadValue;
            newDroneAssignments[droneId].availableCapacity =
              baseCapacity - newDroneAssignments[droneId].totalWeight;
          }
        }
      });

      // Add new assignments from current order selections
      Object.entries(selectedDroneIds).forEach(([packageId, droneId]) => {
        const pkg = listPackage.find((p) => String(p.id) === String(packageId));
        if (!pkg) {
          console.log(`❌ Package not found: ${packageId}`);
          return;
        }

        console.log(
          `➕ Adding package ${packageId} (${pkg.weight}kg) to drone ${droneId} for order ${currentOrderDetails.id}`,
        );

        const crossOrderPackage: CrossOrderPackage = {
          id: pkg.id,
          weight: pkg.weight,
          weightUnit: pkg.weightUnit,
          order_id: pkg.order_id,
          orderId: currentOrderDetails.id,
          orderDetails: currentOrderDetails,
        };

        if (!newDroneAssignments[droneId]) {
          const drone = drones.find((d) => d.doneId === droneId);
          console.log(`🆕 Creating new assignment for drone ${droneId}`);
          // Use availablePayload from API as the baseline available capacity
          const baseCapacity =
            drone?.availablePayload || drone?.maxLoadValue || 0;
          newDroneAssignments[droneId] = {
            droneId,
            packages: [],
            totalWeight: 0,
            availableCapacity: baseCapacity, // This will be recalculated below
            orders: new Set<number>(),
          };
          console.log(
            `🆕 New assignment baseCapacity: ${baseCapacity}kg for drone ${drone?.id}`,
          );
        }

        newDroneAssignments[droneId].packages.push(crossOrderPackage);
        newDroneAssignments[droneId].totalWeight += pkg.weight || 0;
        newDroneAssignments[droneId].orders.add(currentOrderDetails.id);

        // Update available capacity - use original availablePayload as baseline
        const drone = drones.find((d) => d.doneId === droneId);
        if (drone) {
          // availablePayload from API represents current available capacity
          // We need to calculate what the remaining capacity would be after our assignments
          const apiAvailableCapacity =
            drone.availablePayload || drone.maxLoadValue;

          // For our current order assignments, calculate remaining capacity
          const ourOrderWeight = newDroneAssignments[droneId].packages
            .filter((pkg) => pkg.orderId === currentOrderDetails.id)
            .reduce((sum, pkg) => sum + (pkg.weight || 0), 0);

          newDroneAssignments[droneId].availableCapacity =
            apiAvailableCapacity - ourOrderWeight;

          console.log(
            `📊 Updated drone ${droneId}: ourOrderWeight=${ourOrderWeight}kg, apiAvailable=${apiAvailableCapacity}kg, remaining=${newDroneAssignments[droneId].availableCapacity}kg, totalAssigned=${newDroneAssignments[droneId].totalWeight}kg`,
          );
        }
      });

      const updatedGroup = {
        ...group,
        orders: updatedOrders, // Include updated orders array
        droneAssignments: newDroneAssignments,
      };

      console.log('✅ Updated group assignments:', {
        totalAssignments: Object.keys(newDroneAssignments).length,
        assignmentDetails: Object.entries(newDroneAssignments).map(
          ([droneId, assignment]) => ({
            droneId,
            totalWeight: assignment.totalWeight,
            packagesCount: assignment.packages.length,
            orders: Array.from(assignment.orders),
          }),
        ),
      });

      return updatedGroup;
    });
  }, [
    selectedDroneIds,
    listPackage,
    currentOrderDetails,
    generateRouteKey,
    updateRouteGroup,
    drones,
  ]);

  // 📊 Calculate real-time drone assignments
  const globalDroneAssignments = useMemo(() => {
    console.log('🌍 Calculating REAL-TIME global drone assignments...');
    console.log('📊 Dependencies:', {
      dronesCount: drones.length,
      currentOrderId: currentOrderDetails?.id,
      crossOrderStateKeys: Object.keys(crossOrderState.routeGroups),
    });

    const assignments: Record<
      string,
      { assignedWeight: number; availableCapacity: number }
    > = {};

    // Initialize all drones using availablePayload for calculations
    drones.forEach((drone) => {
      // availablePayload from API represents current available capacity
      // maxLoadValue represents total capacity
      const currentAvailableCapacity =
        drone.availablePayload || drone.maxLoadValue;
      assignments[drone.doneId] = {
        assignedWeight: 0, // We'll calculate this from cross-order assignments
        availableCapacity: currentAvailableCapacity,
      };
      console.log(
        `🔧 Initialized drone ${drone.id}: available=${currentAvailableCapacity}kg (availablePayload: ${drone.availablePayload}, maxLoadValue: ${drone.maxLoadValue})`,
      );
    });

    if (!currentOrderDetails) {
      console.log('❌ No current order details');
      return assignments;
    }

    const routeKey = generateRouteKey(currentOrderDetails);
    const routeGroup = crossOrderState.routeGroups[routeKey];

    console.log('🗺️ Route group lookup:', {
      routeKey,
      hasRouteGroup: !!routeGroup,
      hasDroneAssignments: !!routeGroup?.droneAssignments,
      assignmentKeys: routeGroup
        ? Object.keys(routeGroup.droneAssignments || {})
        : [],
    });

    if (routeGroup?.droneAssignments) {
      // Use the updated cross-order assignments
      Object.values(routeGroup.droneAssignments).forEach((assignment) => {
        console.log(
          `📦 Processing assignment for drone ${assignment.droneId}:`,
          {
            totalWeight: assignment.totalWeight,
            availableCapacity: assignment.availableCapacity,
            packagesCount: assignment.packages.length,
            orders: Array.from(assignment.orders),
          },
        );

        if (assignments[assignment.droneId]) {
          assignments[assignment.droneId].assignedWeight =
            assignment.totalWeight;
          assignments[assignment.droneId].availableCapacity =
            assignment.availableCapacity;

          console.log(
            `✅ Updated drone ${assignment.droneId}: ${assignment.totalWeight}kg assigned, ${assignment.availableCapacity}kg available`,
          );
        } else {
          console.log(
            `❌ Drone ${assignment.droneId} not found in assignments object`,
          );
        }
      });
    } else {
      console.log('❌ No drone assignments found in route group');
    }

    console.log('🎯 Final global assignments:', assignments);
    return assignments;
  }, [drones, currentOrderDetails, crossOrderState, generateRouteKey]);

  // 🎯 Optimize drone assignments
  const optimizeDroneAssignments = useCallback(
    (packages: Package[], availableDrones: Drone[]): Record<string, string> => {
      console.log('🔧 Starting optimization...', {
        packages: packages.length,
        drones: availableDrones.length,
      });

      const assignments: Record<string, string> = {};

      // Create working copies with current load calculation using availablePayload
      const workingDrones = availableDrones.map((drone) => {
        const currentAssignment = globalDroneAssignments[drone.doneId];
        const baseCapacity = drone.availablePayload || drone.maxLoadValue;
        return {
          ...drone,
          currentLoad: currentAssignment?.assignedWeight || 0,
          availableCapacity:
            currentAssignment?.availableCapacity || baseCapacity,
        };
      });

      // Sort packages by weight (heaviest first)
      const sortedPackages = [...packages].sort(
        (a, b) => (b.weight || 0) - (a.weight || 0),
      );

      // Sort drones by available capacity (highest first)
      const sortedDrones = [...workingDrones].sort(
        (a, b) => b.availableCapacity - a.availableCapacity,
      );

      console.log(
        '📦 Sorted packages:',
        sortedPackages.map((p) => ({ id: p.id, weight: p.weight })),
      );
      console.log(
        '🚁 Sorted drones:',
        sortedDrones.map((d) => ({
          id: d.id,
          available: d.availableCapacity,
          max: d.maxLoadValue,
        })),
      );

      // Greedy assignment algorithm
      for (const pkg of sortedPackages) {
        const packageWeight = pkg.weight || 0;
        let assigned = false;

        // Find first drone that can fit this package
        for (const drone of sortedDrones) {
          if (drone.availableCapacity >= packageWeight) {
            assignments[pkg.id] = drone.doneId;
            drone.availableCapacity -= packageWeight;
            drone.currentLoad += packageWeight;

            console.log(
              `✅ Assigned package ${pkg.id} (${packageWeight}kg) to drone ${drone.id}, remaining: ${drone.availableCapacity}kg`,
            );
            assigned = true;
            break;
          }
        }

        // If no perfect fit, assign to drone with most capacity (overweight assignment)
        if (!assigned && sortedDrones.length > 0) {
          const bestDrone = sortedDrones[0];
          assignments[pkg.id] = bestDrone.doneId;
          bestDrone.availableCapacity -= packageWeight;
          bestDrone.currentLoad += packageWeight;

          console.warn(
            `⚠️ Overweight assignment: package ${pkg.id} (${packageWeight}kg) to drone ${bestDrone.id}, over by: ${Math.abs(bestDrone.availableCapacity)}kg`,
          );
        }

        // Re-sort drones after assignment
        sortedDrones.sort((a, b) => b.availableCapacity - a.availableCapacity);
      }

      console.log('🎯 Optimization result:', assignments);
      return assignments;
    },
    [globalDroneAssignments],
  );

  // 🔍 Get drone status for UI - combines capacity logic with API disable field
  const getDroneStatus = useCallback(
    (droneId: string, packageWeight: number = 0, drone?: any) => {
      const assignment = globalDroneAssignments[droneId];
      if (!assignment)
        return {
          canFit: false,
          remainingCapacity: 0,
          isOverweight: true,
          disabled: drone?.disabled || false,
          disableReason: drone?.disableReason || null,
        };

      // ✅ Keep existing capacity calculation logic
      const capacityCheck = {
        canFit: assignment.availableCapacity >= packageWeight,
        remainingCapacity: assignment.availableCapacity,
        isOverweight: packageWeight > assignment.availableCapacity,
        assignedWeight: assignment.assignedWeight,
      };

      // 🚫 Combine with API disable field - drone is disabled if either:
      // 1. API says it's disabled, OR
      // 2. Capacity calculation says it can't fit
      const isApiDisabled = drone?.disabled || false;
      const finalCanFit = capacityCheck.canFit && !isApiDisabled;

      return {
        ...capacityCheck,
        canFit: finalCanFit,
        disabled: isApiDisabled,
        disableReason: drone?.disableReason || null,
        // Add detailed reason combining both sources
        combinedDisableReason: isApiDisabled
          ? drone?.disableReason?.detailed_message || 'Drone is not available'
          : !capacityCheck.canFit
            ? 'Insufficient capacity'
            : null,
      };
    },
    [globalDroneAssignments],
  );

  return {
    globalDroneAssignments,
    optimizeDroneAssignments,
    getDroneStatus,
  };
};
