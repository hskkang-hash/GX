import React, { memo, useCallback, useMemo, useState } from 'react';

import { useDrawingModeStore } from '@/features/surveillanceProfile/stores/drawingModeStore';

import MapForRouteUnified from '../../../../components/MapForRouteUnified';
import { WaypointDetails } from '../../../../components/WaypointDetails';
import type { DroneRoute, WaypointDetailsProps } from '../AddNewProfile.d';

interface ProfileMapProps {
  markerData: Array<{
    lat: number;
    lng: number;
    name?: string;
    color?: string;
    operating_altitude?: number;
    routeId?: string | number;
  }>;
  isLineMode: boolean;
  height?: string;
  droneRoutes?: DroneRoute[];
}

const ProfileMapComponent: React.FC<ProfileMapProps> = ({
  markerData = [],
  height,
  droneRoutes,
}) => {
  const [waypointDetails, setWaypointDetails] =
    useState<WaypointDetailsProps | null>(null);

  const currentShape = useDrawingModeStore((state) => state.currentShape);

  const isLineMode = useMemo(
    () => currentShape?.type === 'LINE',
    [currentShape],
  );

  const handleMarkerClick = useCallback(
    (marker: {
      lat: number;
      lng: number;
      name?: string;
      command?: string;
      frame?: string;
      param1?: number;
      param2?: number;
      param3?: number;
      param4?: number;
      color?: string;
      altitude?: number;
      routeId?: string | number;
    }) => {
      const waypointDetails: WaypointDetailsProps = {
        command: marker.command ?? 'WAYPOINT',
        frame: marker.frame ?? 'FRAME',
        param_1: marker.param_1 ?? 0,
        param_2: marker.param_2 ?? 0,
        param_3: marker.param_3 ?? 0,
        param_4: marker.param_4 ?? 0,
        latitude: marker.lat.toString(),
        longitude: marker.lng.toString(),
        altitude: marker.altitude?.toString() || '10.0',
      };

      setWaypointDetails(waypointDetails);
    },
    [],
  );
  return (
    <MapForRouteUnified
      notUseActionButtons
      isLineMode={isLineMode}
      droneRoutes={droneRoutes}
      markerData={markerData.length > 0 ? markerData : []}
      style={{ height: height || '50rem' }}
      overlayContent={
        <WaypointDetails
          waypointDetails={waypointDetails}
          setWaypointDetails={setWaypointDetails}
        />
      }
      onMarkerClick={handleMarkerClick}
    />
  );
};

const ProfileMap = memo(ProfileMapComponent);

export default ProfileMap;
