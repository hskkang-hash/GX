import { Box, Typography, Chip } from '@mui/material';
import React, { useState } from 'react';

interface RouteGroupStatusProps {
  droneAssignmentSummary: Array<{
    droneId: string;
    totalWeight: number;
    availableCapacity: number;
    orders: number[];
    packagesPerOrder: Array<{
      orderId: number;
      packages: Array<{ id: string; weight?: number }>;
    }>;
  }> | null;
  currentOrderId: number;
}

export const RouteGroupStatus: React.FC<RouteGroupStatusProps> = ({
  droneAssignmentSummary,
  currentOrderId,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!droneAssignmentSummary || droneAssignmentSummary.length === 0) {
    return null;
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Box
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <Box
          sx={{
            p: 2,
            bgcolor: 'primary.light',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <Typography
            variant="h6"
            sx={{ color: 'primary.main' }}
          >
            🚁 Route Group Drone Status ({droneAssignmentSummary.length} drones
            active)
          </Typography>
          <Typography sx={{ color: 'primary.main' }}>
            {isExpanded ? '▼' : '▶'}
          </Typography>
        </Box>

        {/* Content */}
        {isExpanded && (
          <Box sx={{ p: 2, bgcolor: 'background.paper' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {droneAssignmentSummary.map((drone) => (
                <Box
                  key={drone.droneId}
                  sx={{
                    p: 2,
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    bgcolor: 'background.default',
                  }}
                >
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      mb: 1,
                    }}
                  >
                    <Typography
                      variant="subtitle1"
                      fontWeight="bold"
                    >
                      Drone {drone.droneId}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Chip
                        label={`${drone.totalWeight}kg assigned`}
                        size="small"
                        sx={{ bgcolor: '#FFECB3', color: '#E65100' }}
                      />
                      <Chip
                        label={`${drone.availableCapacity}kg available`}
                        size="small"
                        sx={{
                          bgcolor:
                            drone.availableCapacity > 0 ? '#E8F5E8' : '#FFEBEE',
                          color:
                            drone.availableCapacity > 0 ? '#2E7D32' : '#C62828',
                        }}
                      />
                    </Box>
                  </Box>

                  <Typography
                    variant="body2"
                    sx={{ mb: 1, color: 'text.secondary' }}
                  >
                    Active in {drone.orders.length} order(s):{' '}
                    {drone.orders.join(', ')}
                  </Typography>

                  <Box
                    sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}
                  >
                    {drone.packagesPerOrder.map((orderInfo) => (
                      <Box
                        key={orderInfo.orderId}
                        sx={{
                          p: 1,
                          bgcolor:
                            orderInfo.orderId === currentOrderId
                              ? '#E3F2FD'
                              : '#F5F5F5',
                          borderRadius: 0.5,
                          opacity:
                            orderInfo.orderId === currentOrderId ? 1 : 0.7,
                          border:
                            orderInfo.orderId === currentOrderId
                              ? '1px solid #2196F3'
                              : 'none',
                        }}
                      >
                        <Typography
                          variant="body2"
                          fontWeight="medium"
                        >
                          Order {orderInfo.orderId}{' '}
                          {orderInfo.orderId === currentOrderId
                            ? '(Current)'
                            : ''}
                        </Typography>
                        <Box
                          sx={{
                            display: 'flex',
                            gap: 0.5,
                            flexWrap: 'wrap',
                            mt: 0.5,
                          }}
                        >
                          {orderInfo.packages.map((pkg) => (
                            <Chip
                              key={pkg.id}
                              label={`Package ${pkg.id} (${pkg.weight || 0}kg)`}
                              size="small"
                              variant="outlined"
                              sx={{ fontSize: '0.7rem', height: '20px' }}
                            />
                          ))}
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </Box>
              ))}
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
};
