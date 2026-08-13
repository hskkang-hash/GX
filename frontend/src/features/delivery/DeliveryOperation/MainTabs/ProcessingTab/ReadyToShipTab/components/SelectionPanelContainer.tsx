import { Box, Divider } from '@mui/material';
import { memo } from 'react';
import { useTheme } from 'rj-core';

import { Drone, Package } from '../types';
import DroneSelectionPanel from './DroneSelectionPanel';
import { RouteSelectionPanel } from './RouteSelectionPanel';

interface SelectionPanelContainerProps {
  // Route props
  routes: any[];
  selectedRouteId: number | null;
  onRouteSelect: (routeId: number) => void;

  // Drone props
  drones: Drone[];
  selectedPackageIdx: string | null;
  selectedDroneIds: Record<string, string>;
  globalDroneAssignments: Record<string, any>;
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
  getDroneStatus: (droneId: string, packageWeight?: number) => any;
  onPackageSelection: (packageId: string) => void;
  disabledAssignPackage: boolean;
  onAssignPackage: () => Promise<void>;
  isSubmitting: boolean;

  // Loading states
  isLoading: boolean;
  height?: number;
}

export const SelectionPanelContainer = memo(
  ({
    routes,
    selectedRouteId,
    onRouteSelect,
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
    onPackageSelection,
    disabledAssignPackage,
    onAssignPackage,
    isSubmitting,
    isLoading,
    height = 400,
  }: SelectionPanelContainerProps) => {
    const [theme] = useTheme();
    console.log('selectedRouteId', selectedRouteId);

    return (
      <Box
        display="flex"
        flex={2}
        gap={2}
        bgcolor={theme === 'dark' ? '#1F1F20' : '#FFFFFF'}
        borderRadius={2}
        p={2}
        height={height}
      >
        <RouteSelectionPanel
          routes={routes}
          selectedRouteId={selectedRouteId}
          isLoading={isLoading}
          onRouteSelect={onRouteSelect}
        />

        <Divider
          orientation="vertical"
          flexItem
          sx={{
            borderColor: theme === 'dark' ? '#444646' : '#DDDFE2',
          }}
        />

        <DroneSelectionPanel
          drones={drones}
          selectedPackageIdx={selectedPackageIdx}
          selectedDroneIds={selectedDroneIds}
          globalDroneAssignments={globalDroneAssignments}
          optimizedAssignments={optimizedAssignments}
          listPackage={listPackage}
          isLoadingMoreDrones={isLoadingMoreDrones}
          hasMoreDrones={hasMoreDrones}
          hasTriedLoadMoreDrones={hasTriedLoadMoreDrones}
          onDroneSelection={onDroneSelection}
          onDroneLocationChange={onDroneLocationChange}
          onDroneScroll={onDroneScroll}
          getDroneStatus={getDroneStatus}
          onPackageSelection={onPackageSelection}
          disabledAssignPackage={disabledAssignPackage}
          onAssignPackage={onAssignPackage}
          isSubmitting={isSubmitting}
        />
      </Box>
    );
  },
);

SelectionPanelContainer.displayName = 'SelectionPanelContainer';
