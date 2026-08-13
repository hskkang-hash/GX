import {
  Box,
  Typography,
  Radio,
  Chip,
  CircularProgress,
  Tooltip,
  styled,
  tooltipClasses,
} from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CustomBtn, ROLE_PERMISSION, useTheme } from 'rj-core';

import { Drone, Package } from '../types';

const CustomWidthTooltip = styled(({ className, ...props }) => (
  <Tooltip
    {...props}
    classes={{ popper: className }}
  />
))({
  [`& .${tooltipClasses.tooltip}`]: {
    maxWidth: '30rem',
  },
});

interface DroneSelectionPanelProps {
  drones: Drone[];
  selectedPackageIdx: string | null;
  selectedDroneIds: Record<string, string>;
  globalDroneAssignments: Record<
    string,
    { assignedWeight: number; availableCapacity: number }
  >;
  optimizedAssignments: Record<string, string>;
  listPackage: Package[];
  isLoadingMoreDrones: boolean;
  hasMoreDrones: boolean;
  hasTriedLoadMoreDrones: boolean;
  onDroneSelection: (packageId: string, droneId: string) => void;
  onDroneLocationChange: (
    location: { lat: number; lng: number } | null,
  ) => void;
  onDroneScroll: (event: any) => void;
  // Add new prop for getting drone status
  getDroneStatus?: (
    droneId: string,
    packageWeight: number,
  ) => {
    canFit: boolean;
    remainingCapacity: number;
    isOverweight: boolean;
    assignedWeight: number;
  };
  // ⭐ Add package selection handler
  onPackageSelection: (packageId: string) => void;
  disabledAssignPackage: boolean;
  disabledReason?: string;
  onAssignPackage: () => void;
  isSubmitting: boolean;
}

const DroneSelectionPanel: React.FC<DroneSelectionPanelProps> = ({
  drones,
  selectedPackageIdx,
  selectedDroneIds,
  globalDroneAssignments,
  optimizedAssignments,
  listPackage,
  isLoadingMoreDrones,
  hasMoreDrones,
  hasTriedLoadMoreDrones,
  onDroneSelection,
  onDroneLocationChange,
  onDroneScroll,
  getDroneStatus,
  onPackageSelection, // ⭐ Add this prop
  disabledAssignPackage,
  disabledReason,
  onAssignPackage,
  isSubmitting,
}) => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  return (
    <Box flex={1}>
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={2}
      >
        <Typography
          variant="h6"
          fontWeight={600}
          fontSize={'1.25rem'}
        >
          {t('Select Drone')}
        </Typography>
        <Box
          display="flex"
          gap={2}
          alignItems="center"
        >
          <Tooltip
            title={
              disabledAssignPackage
                ? disabledReason || 'Button disabled'
                : t('Submit drone assignments')
            }
            placement="top"
          >
            <span>
              <CustomBtn
                actionType={ROLE_PERMISSION.UPDATE}
                variant="contained"
                color="primary"
                size="medium"
                label={t('Assign All')}
                style={{ minWidth: 100, borderRadius: 8 }}
                disabled={disabledAssignPackage}
                onClick={onAssignPackage}
                loading={isSubmitting}
              />
            </span>
          </Tooltip>
        </Box>
      </Box>
      <Box
        display="flex"
        gap={1}
        sx={{
          height: 'calc(400px - 2rem - 1rem - 2rem)',
        }}
      >
        {/* Package Tabs - vertical */}
        <Box
          display="flex"
          flexDirection="column"
          gap={2}
          sx={{
            height: 'calc(400px - 2rem - 1rem - 3rem)',
            overflow: 'auto',
          }}
        >
          {listPackage.length === 0 && (
            <Box
              display="flex"
              justifyContent="center"
              alignItems="center"
              height="100%"
            >
              <Typography color="#757575">{t('No package found')}</Typography>
            </Box>
          )}
          {listPackage.length > 1 &&
            listPackage.map((pkg, idx) => (
              <Tooltip
                title={
                  pkg?.weight && (
                    <Box
                      display="flex"
                      gap={1}
                    >
                      <Typography>{t('Weight')}</Typography>
                      <Chip
                        label={`${pkg.weight}${pkg.weightUnit || 'kg'}`}
                        size="small"
                        sx={{
                          fontSize: '0.75rem',
                          height: '20px',
                          fontWeight: 500,
                          borderRadius: '0.25rem',
                          bgcolor: theme === 'dark' ? '#444646' : '#E0E0E0',
                        }}
                      />
                    </Box>
                  )
                }
              >
                <Box
                  onClick={() => {
                    console.log('📦 Package selected:', pkg.id);
                    onPackageSelection(pkg.id);
                  }}
                  key={pkg.id}
                  p="0.5rem 1rem"
                  borderRadius="0.5rem"
                  bgcolor={
                    selectedPackageIdx === pkg.id
                      ? theme === 'dark'
                        ? '#293438'
                        : '#EEF9FF'
                      : theme === 'dark'
                        ? '#2D2E30'
                        : '#F6F7F8'
                  }
                  color={
                    selectedPackageIdx === pkg.id
                      ? theme === 'dark'
                        ? 'var(--ga-primary-dark)'
                        : 'var(--ga-primary)'
                      : '#9C9D9D'
                  }
                  fontWeight={selectedPackageIdx === pkg.id ? 700 : 500}
                  fontSize={'1rem'}
                  sx={{
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    opacity: selectedPackageIdx === pkg.id ? 1 : 0.7,
                    '&:hover': {
                      opacity: 1,
                      transform: 'translateY(-1px)',
                    },
                  }}
                >
                  <Box
                    display="flex"
                    justifyContent="space-between"
                    alignItems="center"
                  >
                    <span>
                      {t('Package')} {idx + 1}
                    </span>
                  </Box>
                </Box>
              </Tooltip>
            ))}
        </Box>

        {/* Drone List */}
        <Box
          flex={1}
          borderRadius={'0.5rem'}
          bgcolor={theme === 'dark' ? '#2D2E30' : '#F6F7F8'}
          p="1rem"
          sx={{
            height: 'calc(400px - 2rem - 1rem - 3rem)',
            overflow: 'hidden',
          }}
        >
          <Box
            overflow="auto"
            height={400 - 32 - 27 - 32}
            maxHeight={500}
            onScroll={onDroneScroll}
            sx={{
              overflow: 'auto',
            }}
          >
            {drones.length === 0 &&
              selectedPackageIdx &&
              !isLoadingMoreDrones && (
                <Box
                  display="flex"
                  justifyContent="center"
                  alignItems="start"
                  height="100%"
                >
                  <Typography color="#757575">
                    {t(
                      "Sorry! We couldn't find a suitable drone for the selected package. Please try again later.",
                    )}
                  </Typography>
                </Box>
              )}
            {drones.length > 0 &&
              drones.map((drone) => {
                const selectedPackage = selectedPackageIdx
                  ? listPackage.find((p) => p.id === selectedPackageIdx)
                  : null;
                const packageWeight = selectedPackage?.weight || 0;

                // 🎯 Use the new getDroneStatus function for accurate calculation
                const droneStatus = getDroneStatus
                  ? getDroneStatus(drone.doneId, packageWeight, drone)
                  : {
                      canFit: true,
                      remainingCapacity: drone.maxLoadValue,
                      isOverweight: false,
                      assignedWeight: 0,
                      disabled: drone?.disabled || false,
                      disableReason: drone?.disableReason || null,
                      combinedDisableReason: null,
                    };

                const isCurrentlySelected =
                  selectedDroneIds[selectedPackageIdx || ''] === drone.doneId;
                const isOptimized =
                  optimizedAssignments[selectedPackageIdx || ''] ===
                  drone.doneId;

                // 📊 Use accurate values from droneStatus
                const {
                  canFit,
                  remainingCapacity,
                  isOverweight,
                  assignedWeight,
                  disabled: isApiDisabled,
                  combinedDisableReason,
                } = droneStatus;

                // 🔍 Get cross-order assignment info for this drone
                const crossOrderInfo = (() => {
                  if (!globalDroneAssignments[drone.doneId]) return null;

                  // This would come from route group assignments
                  const assignment = globalDroneAssignments[drone.doneId];
                  const otherOrderWeight = assignment.assignedWeight;
                  const currentOrderWeight =
                    selectedDroneIds[selectedPackageIdx || ''] === drone.doneId
                      ? packageWeight
                      : 0;

                  return {
                    otherOrderWeight: otherOrderWeight - currentOrderWeight,
                    currentOrderWeight,
                    totalWeight: otherOrderWeight,
                  };
                })();

                console.log(`🚁 Drone ${drone.id} status:`, {
                  packageWeight,
                  assignedWeight,
                  remainingCapacity,
                  maxLoad: drone.maxLoadValue,
                  canFit,
                  isOverweight,
                  isCurrentlySelected,
                  isOptimized,
                  crossOrderInfo,
                });

                return (
                  <Box
                    key={drone.id}
                    display="flex"
                    flexDirection="column"
                    alignItems="flex-start"
                    border="1.5px solid"
                    borderColor={
                      isOptimized
                        ? theme === 'dark'
                          ? '#4CAF50'
                          : '#4CAF50'
                        : isCurrentlySelected
                          ? theme === 'dark'
                            ? '#2196F3'
                            : '#2196F3'
                          : theme === 'dark'
                            ? '#444646'
                            : '#DDDFE2'
                    }
                    bgcolor={theme === 'dark' ? '#1F1F20' : '#fff'}
                    borderRadius={3}
                    mb={'1rem'}
                    p={'1rem'}
                    sx={{
                      cursor: canFit ? 'pointer' : 'not-allowed',
                      transition: 'border-color 0.2s, box-shadow 0.2s',
                      position: 'relative',
                      opacity: canFit || isCurrentlySelected ? 1 : 0.6,
                    }}
                    onClick={() => {
                      if (canFit && selectedPackageIdx) {
                        onDroneSelection(selectedPackageIdx, drone.doneId);
                        onDroneLocationChange(drone.droneLocation);
                      }
                    }}
                  >
                    <Box
                      display="flex"
                      alignItems="center"
                      justifyContent="space-between"
                      width="100%"
                    >
                      <CustomWidthTooltip
                        title={
                          !isCurrentlySelected && (
                            <>
                              <Box
                                mt={1}
                                display="grid"
                                gridTemplateColumns="140px 1fr"
                                rowGap={0.5}
                                columnGap={2}
                                fontSize={'0.9rem'}
                              >
                                <Box>{t('Max Load')}</Box>
                                <Box>{drone.maxLoad}</Box>
                                <Box>{t('Available Load')}</Box>
                                <Box>{`${drone.availablePayload} ${drone.maxLoadUnit}`}</Box>
                                <Box>{t('Available Remaining')}</Box>
                                <Box>{`${remainingCapacity} ${drone.maxLoadUnit}`}</Box>
                              </Box>

                              {combinedDisableReason && (
                                <Box
                                  fontSize={'0.9rem'}
                                  mt={1}
                                >
                                  {combinedDisableReason}
                                </Box>
                              )}
                            </>
                          )
                        }
                        placement="top"
                      >
                        <Box
                          display="flex"
                          alignItems="center"
                          width="100%"
                        >
                          <Radio
                            checked={isCurrentlySelected}
                            disabled={!canFit}
                            onChange={() =>
                              canFit &&
                              selectedPackageIdx &&
                              onDroneSelection(selectedPackageIdx, drone.doneId)
                            }
                            sx={{
                              color: '#2196F3',
                              padding: 0,
                              mr: 1,
                              '&.Mui-checked': { color: '#2196F3' },
                            }}
                          />
                          <Typography
                            fontWeight={400}
                            fontSize={'1rem'}
                          >
                            {drone.name}
                          </Typography>
                        </Box>
                      </CustomWidthTooltip>

                      {/* <Box
                        display="flex"
                        gap={1}
                      >
                        {isOptimized && (
                          <Chip
                            label="Optimized"
                            size="small"
                            sx={{
                              fontSize: '0.7rem',
                              height: '18px',
                              bgcolor: '#4CAF50',
                              color: 'white',
                            }}
                          />
                        )}
                        {isCurrentlySelected && canFit && !isOverweight && (
                          <Chip
                            label="Auto-Selected"
                            size="small"
                            sx={{
                              fontSize: '0.7rem',
                              height: '18px',
                              bgcolor: '#2196F3',
                              color: 'white',
                            }}
                          />
                        )}
                        {isOverweight && (
                          <Chip
                            label="Overweight"
                            size="small"
                            sx={{
                              fontSize: '0.7rem',
                              height: '18px',
                              bgcolor: '#f44336',
                              color: 'white',
                            }}
                          />
                        )}
                        {canFit && !isOverweight && packageWeight > 0 && !isCurrentlySelected && (
                          <Chip
                            label="Can Fit"
                            size="small"
                            sx={{
                              fontSize: '0.7rem',
                              height: '18px',
                              bgcolor: '#4CAF50',
                              color: 'white',
                            }}
                          />
                        )}
                      </Box> */}
                    </Box>
                    {isCurrentlySelected && (
                      <Box
                        mt={1}
                        py={1}
                        display="grid"
                        gridTemplateColumns="1fr 1fr"
                        rowGap={0.5}
                        columnGap={2}
                        fontSize={'0.9rem'}
                        width={'100%'}
                        sx={{
                          borderTop: '1.5px solid',
                          borderColor: theme === 'dark' ? '#444646' : '#DDDFE2',
                        }}
                      >
                        <Box>{t('Model')}</Box>
                        <Box>{drone.model}</Box>

                        <Box>{t('Battery')}</Box>
                        <Box>{drone.battery}</Box>

                        <Box>{t('Max Load')}</Box>
                        <Box>{drone.maxLoad}</Box>

                        <Box>{t('Available Load')}</Box>
                        <Box>{`${drone.availablePayload} ${drone.maxLoadUnit}`}</Box>

                        {/* <Box color="#757575">Total Assigned</Box>
                      <Box>
                        <Chip
                          label={`${assignedWeight} ${drone.maxLoadUnit}`}
                          size="small"
                          sx={{
                            fontSize: '0.7rem',
                            height: '18px',
                            bgcolor:
                              assignedWeight > 0
                                ? '#FFECB3'
                                : theme === 'dark'
                                  ? '#444646'
                                  : '#E0E0E0',
                            color:
                              assignedWeight > 0 ? '#E65100' : theme === 'dark' ? '#fff' : '#000',
                          }}
                        />
                      </Box>

                      {crossOrderInfo && crossOrderInfo.otherOrderWeight > 0 && (
                        <>
                          <Box color="#757575">Other Orders</Box>
                          <Box>
                            <Chip
                              label={`${crossOrderInfo.otherOrderWeight} ${drone.maxLoadUnit}`}
                              size="small"
                              sx={{
                                fontSize: '0.7rem',
                                height: '18px',
                                bgcolor: '#E1F5FE',
                                color: '#0277BD',
                              }}
                            />
                          </Box>
                        </>
                      )} */}

                        <Box>{t('Available Remaining')}</Box>
                        <Box>
                          <Chip
                            label={`${remainingCapacity} ${drone.maxLoadUnit}`}
                            size="small"
                            sx={{
                              fontSize: '0.875rem',
                              height: '1.5rem',
                              fontWeight: 600,
                              bgcolor:
                                remainingCapacity > 0 ? '#E8F5E8' : '#FFEBEE',
                              color:
                                remainingCapacity > 0 ? '#2E7D32' : '#C62828',
                              borderRadius: '0.5rem',
                            }}
                          />
                        </Box>
                      </Box>
                    )}
                  </Box>
                );
              })}
            {isLoadingMoreDrones && (
              <Box
                display="flex"
                justifyContent="center"
                p={2}
              >
                <CircularProgress size={20} />
              </Box>
            )}
            {/* {!hasMoreDrones && drones.length > 0 && hasTriedLoadMoreDrones && (
              <Box
                display="flex"
                justifyContent="center"
                p={2}
              >
                <Typography
                  variant="body2"
                  color={theme === 'dark' ? '#fff' : '#000'}
                >
                  No more drones to load
                </Typography>
              </Box>
            )} */}
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default DroneSelectionPanel;
