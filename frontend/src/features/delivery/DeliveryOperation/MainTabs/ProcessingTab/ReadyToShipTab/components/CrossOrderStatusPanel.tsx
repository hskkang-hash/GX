import { Box, Typography, Chip } from '@mui/material';
import React from 'react';
import { CustomBtn } from 'rj-core';

import { RouteGroup } from '../hooks/useCrossOrderState';
import { OrderRow } from '../types';

interface CrossOrderStatusPanelProps {
  currentOrderDetails: OrderRow | null;
  routeGroup: RouteGroup | null;
  routeKey: string;
  onOptimize: (routeKey: string) => void;
}

export const CrossOrderStatusPanel: React.FC<CrossOrderStatusPanelProps> = ({
  currentOrderDetails,
  routeGroup,
  routeKey,
  onOptimize,
}) => {
  if (!currentOrderDetails || !routeGroup) {
    return null;
  }

  const completedOrders = new Set<number>();
  const incompleteOrders = new Set<number>();

  // Check completion status for each order
  routeGroup.orders.forEach((order) => {
    const orderPackages = routeGroup.allPackages.filter(
      (pkg) => pkg.orderId === order.id,
    );
    const hasAssignments = orderPackages.some((pkg) =>
      Object.values(routeGroup.droneAssignments || {}).some((drone) =>
        drone.packages.some((p) => p.id === pkg.id),
      ),
    );

    const allPackagesAssigned = orderPackages.every((pkg) =>
      Object.values(routeGroup.droneAssignments || {}).some((drone) =>
        drone.packages.some((p) => p.id === pkg.id),
      ),
    );

    if (allPackagesAssigned && orderPackages.length > 0) {
      completedOrders.add(order.id);
    } else if (hasAssignments) {
      incompleteOrders.add(order.id);
    }
  });
  console.log('routegroup22222    ', routeGroup);

  return (
    <Box
      sx={{
        mb: 2,
        p: 2,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
      }}
    >
      <Typography
        variant="h6"
        sx={{ mb: 1, color: 'primary.main' }}
      >
        Cross-Order Route Group Status
      </Typography>

      <Box>
        <Typography
          variant="body2"
          sx={{ mb: 1 }}
        >
          Route: <strong>{routeKey}</strong>
        </Typography>
        <Typography
          variant="body2"
          sx={{ mb: 1 }}
        >
          Orders in group: <strong>{routeGroup.orders.length}</strong>
        </Typography>
        <Typography
          variant="body2"
          sx={{ mb: 1 }}
        >
          Total packages: <strong>{routeGroup.allPackages.length}</strong>
        </Typography>

        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
          {routeGroup.orders.map((order) => (
            <>
              {' '}
              <Chip
                key={order.id}
                label={`Order ${order.order_id}`}
                size="small"
                sx={{
                  bgcolor: completedOrders.has(order.id)
                    ? 'success.main'
                    : incompleteOrders.has(order.id)
                      ? 'warning.main'
                      : 'grey.400',
                  color: 'white',
                  fontSize: '0.7rem',
                }}
              />
              <Chip
                key={order.order_id}
                label={`Order ${order.order_id}`}
                size="small"
                sx={{
                  bgcolor: completedOrders.has(order.id)
                    ? 'success.main'
                    : incompleteOrders.has(order.id)
                      ? 'warning.main'
                      : 'grey.400',
                  color: 'white',
                  fontSize: '0.7rem',
                }}
              />
            </>
          ))}
        </Box>

        {Object.keys(routeGroup.droneAssignments || {}).length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography
              variant="body2"
              sx={{ mb: 1, fontWeight: 'bold' }}
            >
              Drone Assignments:
            </Typography>
            {Object.values(routeGroup.droneAssignments).map((assignment) => (
              <Box
                key={assignment.droneId}
                sx={{ ml: 1, mb: 1 }}
              >
                <Typography variant="body2">
                  Drone {assignment.droneId}: {assignment.packages.length}{' '}
                  packages ({assignment.totalWeight}kg) - Orders:{' '}
                  {Array.from(assignment.orders).join(', ')}
                </Typography>
              </Box>
            ))}
          </Box>
        )}

        {incompleteOrders.size > 0 && (
          <Typography
            variant="body2"
            sx={{ mt: 1, color: 'warning.main' }}
          >
            ⚠️ Orders {Array.from(incompleteOrders).join(', ')} are incomplete
            and will be excluded from delivery
          </Typography>
        )}

        {/* Cross-Order Optimization Button */}
        <Box sx={{ mt: 2 }}>
          <CustomBtn
            variant="outlined"
            size="small"
            onClick={() => onOptimize(routeKey)}
            disabled={routeGroup.allPackages.length === 0}
          >
            Re-optimize Cross-Order Assignments
          </CustomBtn>
        </Box>
      </Box>
    </Box>
  );
};
