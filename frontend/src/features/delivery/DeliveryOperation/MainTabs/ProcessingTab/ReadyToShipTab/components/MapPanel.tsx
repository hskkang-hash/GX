import { Box } from '@mui/material';
import { memo, useMemo } from 'react';

import { Map } from '@/components/maps';

interface MapPanelProps {
  routes: any[];
  routesMap: any[];
  droneLocation?: { lat: number; lng: number } | null;
  height?: number;
}

export const MapPanel = memo(
  ({ routes, routesMap, droneLocation, height = 400 }: MapPanelProps) => {
    // Helper function to ensure proper coordinate format
    const normalizeCoordinate = (coord: any): number => {
      if (typeof coord === 'number') return coord;
      const parsed = Number(coord);
      return isNaN(parsed) ? 0 : parsed;
    };

    // Helper function to create a safe center object
    const createSafeCenter = (
      obj: any,
    ): { lat: number; lng: number } | undefined => {
      if (
        !obj ||
        (typeof obj.lat === 'undefined' && typeof obj.latitude === 'undefined')
      )
        return undefined;

      const lat = normalizeCoordinate(obj.lat || obj.latitude);
      const lng = normalizeCoordinate(obj.lng || obj.longitude);

      if (lat === 0 && lng === 0) return undefined;

      return { lat, lng };
    };

    // Determine map markers and properties
    const mapProps = useMemo(() => {
      const hasRoutes = routes.length > 0 && routesMap.length > 0;

      if (hasRoutes) {
        const safeCenter = routesMap[0]
          ? createSafeCenter(routesMap[0])
          : undefined;

        return {
          center: safeCenter,
          operatingMarkers: routesMap,
          standbyMarkers: droneLocation ? [droneLocation] : [], // Show drone as standby marker
          polylines: [routesMap],
          fitBounds: true, // Let map auto-calculate bounds
          boundsPadding: 0.15, // 15% padding for better visibility
        };
      }

      if (droneLocation) {
        const safeCenter = createSafeCenter(droneLocation);

        return {
          center: safeCenter,
          level: 8, // Close zoom for single drone
          operatingMarkers: [droneLocation],
          standbyMarkers: [],
          polylines: [],
          fitBounds: false, // Use manual level for single point
        };
      }

      return {
        center: { lat: 37.5665, lng: 126.978 }, // Default to Seoul
        level: 8,
        operatingMarkers: [],
        standbyMarkers: [],
        polylines: [],
        fitBounds: false,
      };
    }, [routes, routesMap, droneLocation]);

    return (
      <Box flex={1}>
        <Map
          {...mapProps}
          style={{ height }}
        />
      </Box>
    );
  },
);

MapPanel.displayName = 'MapPanel';
