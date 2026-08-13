import { useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { ToastTopHelper } from 'rj-core';

import API, { endpoint } from '../../../../../../../services/API';
import { OrderRow } from '../types';

interface UseApiSubmissionProps {
  currentOrderDetails: OrderRow | null;
  selectedRouteId: number | null;
  generateRouteKey: (order: OrderRow) => string;
  getRouteGroup: (routeKey: string) => any;
}

export const useApiSubmission = ({
  currentOrderDetails,
  selectedRouteId,
  generateRouteKey,
  getRouteGroup,
}: UseApiSubmissionProps) => {
  const { t } = useTranslation();
  // Memoized API payload transformation
  const getApiPayload = useMemo(() => {
    if (!currentOrderDetails || !selectedRouteId) {
      return { route_id: null, drone_ids: [] };
    }

    const routeKey = generateRouteKey(currentOrderDetails);
    const routeGroup = getRouteGroup(routeKey);

    console.log('🔍 Route group debug:', {
      routeKey,
      hasRouteGroup: !!routeGroup,
      routeGroupOrders: routeGroup?.orders?.length || 0,
      routeGroupOrderIds:
        routeGroup?.orders?.map((o) => ({
          id: o.id,
          order_id: o.order_id,
          real_order_id: o.real_order_id,
        })) || [],
      currentOrderId: currentOrderDetails.id,
      currentOrderRealId: currentOrderDetails.real_order_id,
      hasDroneAssignments: !!routeGroup?.droneAssignments,
      droneAssignmentsCount: Object.keys(routeGroup?.droneAssignments || {})
        .length,
    });

    if (
      !routeGroup?.droneAssignments ||
      Object.keys(routeGroup.droneAssignments).length === 0
    ) {
      return { route_id: selectedRouteId, drone_ids: [] };
    }

    const droneIds: Array<{
      drone_id: string;
      orders: Array<{
        order_id: number;
        package_ids: string[];
        real_order_id?: string;
      }>;
    }> = [];

    // Process drone assignments
    Object.values(routeGroup.droneAssignments).forEach((assignment: any) => {
      const orderGroups: Record<number, string[]> = {};
      console.log('assignment', assignment);
      assignment.packages.forEach((pkg: any) => {
        const orderId = Number(pkg.orderId);
        if (!orderGroups[orderId]) {
          orderGroups[orderId] = [];
        }
        orderGroups[orderId].push(pkg.id);
      });

      if (Object.keys(orderGroups).length > 0) {
        const orders = Object.entries(orderGroups).map(
          ([orderIdStr, packageIds]) => {
            const orderId = Number(orderIdStr);
            const orderDetails = routeGroup?.orders.find(
              (order: any) => order.id === orderId,
            );
            console.log('🔍 Order mapping:', {
              internalOrderId: orderId,
              orderDetails: orderDetails,
              realOrderId: orderDetails?.order_id,
              realOrderIdField: orderDetails?.real_order_id,
            });
            return {
              order_id: orderId,
              package_ids: packageIds,
              real_order_id:
                orderDetails?.real_order_id || orderDetails?.order_id, // Use real_order_id if available
            };
          },
        );

        droneIds.push({
          drone_id: assignment.droneId,
          orders,
        });
      }
    });

    return { route_id: selectedRouteId, drone_ids: droneIds };
  }, [currentOrderDetails, selectedRouteId, generateRouteKey, getRouteGroup]);

  // Validation function
  const validateAssignments = useCallback(() => {
    const apiData = getApiPayload;

    const validation = {
      isValid: true,
      errors: [] as string[],
      warnings: [] as string[],
      summary: {
        totalDrones: apiData.drone_ids.length,
        totalOrders: new Set(
          apiData.drone_ids.flatMap((d) => d.orders.map((o) => o.order_id)),
        ).size,
        totalPackages: apiData.drone_ids.reduce(
          (sum, drone) =>
            sum +
            drone.orders.reduce(
              (orderSum, order) => orderSum + order.package_ids.length,
              0,
            ),
          0,
        ),
      },
    };

    // Basic validations
    if (!apiData.route_id) {
      validation.errors.push('Route ID is required');
      validation.isValid = false;
    }

    if (apiData.drone_ids.length === 0) {
      validation.errors.push('No drone assignments found');
      validation.isValid = false;
    }

    // Check for duplicate package assignments
    const allPackageIds = apiData.drone_ids.flatMap((d) =>
      d.orders.flatMap((o) => o.package_ids),
    );
    const uniquePackageIds = new Set(allPackageIds);

    if (allPackageIds.length !== uniquePackageIds.size) {
      validation.errors.push('Duplicate package assignments detected');
      validation.isValid = false;
    }

    return {
      ...validation,
      apiData,
    };
  }, [getApiPayload]);

  // Submit function
  const submitAssignments = useCallback(async () => {
    console.log('🚀 Submitting drone assignments...');

    const validation = validateAssignments();

    if (!validation.isValid) {
      console.error('❌ Validation failed:', validation.errors);
      ToastTopHelper.error(validation.errors.join(', '));
      return false;
    }
    console.log('validation.apiData', validation.apiData);

    try {
      // Transform payload for API
      const transformedPayload = {
        ...validation.apiData,
        drone_ids: validation.apiData.drone_ids.map((drone) => ({
          ...drone,
          orders: drone.orders.map((order) => ({
            order_id: order.real_order_id || order.order_id, // Use real_order_id if available
            package_ids: order.package_ids,
          })),
        })),
      };

      console.log('🔄 API Payload transformation:', {
        original: validation.apiData,
        transformed: transformedPayload,
        orderMappings: transformedPayload.drone_ids.map((drone) => ({
          droneId: drone.drone_id,
          orders: drone.orders.map((order, idx) => {
            const originalOrder = validation.apiData.drone_ids.find(
              (d) => d.drone_id === drone.drone_id,
            )?.orders[idx];
            return {
              internal_order_id: originalOrder?.order_id,
              real_order_id: originalOrder?.real_order_id,
              api_order_id: order.order_id, // This shows what will be sent to API
            };
          }),
        })),
      });

      console.log('📤 Submitting payload:', transformedPayload);

      const response = await API.post(
        endpoint.assignPackageToDrone,
        transformedPayload,
      );

      if (
        response?.success &&
        Array.isArray(response?.data?.assigned_orders) &&
        response?.data?.assigned_orders?.length > 0
      ) {
        if (response.message) {
          ToastTopHelper.success(response.message);
        }
        console.log('✅ Drone assignments submitted successfully');
        return true;
      } else {
        console.error('❌ API responded with error');
        ToastTopHelper.error(t('Packages assigned to drones failed'));
        return false;
      }
    } catch (error) {
      console.error('❌ Failed to submit drone assignments:', error);
      ToastTopHelper.error('Failed to submit drone assignments');
      return false;
    }
  }, [validateAssignments]);

  // Get assignment summary
  const getAssignmentsSummary = useCallback(() => {
    const apiData = getApiPayload;

    return {
      totalDrones: apiData.drone_ids.length,
      totalOrders: new Set(
        apiData.drone_ids.flatMap((d) => d.orders.map((o) => o.order_id)),
      ).size,
      totalPackages: apiData.drone_ids.reduce(
        (sum, drone) =>
          sum +
          drone.orders.reduce(
            (orderSum, order) => orderSum + order.package_ids.length,
            0,
          ),
        0,
      ),
      droneDetails: apiData.drone_ids.map((drone) => ({
        droneId: drone.drone_id,
        ordersCount: drone.orders.length,
        packagesCount: drone.orders.reduce(
          (sum, order) => sum + order.package_ids.length,
          0,
        ),
      })),
    };
  }, [getApiPayload]);

  // Check if assignments can be submitted
  const canSubmit = useMemo(() => {
    const validation = validateAssignments();
    return validation.isValid;
  }, [validateAssignments]);

  return {
    submitAssignments,
    validateAssignments,
    getAssignmentsSummary,
    canSubmit,
    getApiPayload,
  };
};
