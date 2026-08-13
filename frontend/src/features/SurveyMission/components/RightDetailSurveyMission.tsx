import { useCallback, useMemo, useState } from 'react';

import { useDrawingModeStore } from '../stores/drawingModeStore';
import MapForRouteUnified from './MapForRouteUnified';
import { WaypointDetails, WaypointDetailsProps } from './WaypointDetails';

export const RightDetailSurveyMission = ({
  markerData = [],
}: {
  markerData?: { lat: number; lng: number; name?: string; color?: string }[];
}) => {
  const [waypointDetails, setWaypointDetails] =
    useState<WaypointDetailsProps | null>(null);

  const currentShape = useDrawingModeStore((state) => state.currentShape);

  const isLineMode = useMemo(
    () => currentShape?.type === 'LINE',
    [currentShape],
  );

  const handleMarkerClick = useCallback(
    (marker: { lat: number; lng: number; name?: string; color?: string }) => {
      // Create waypoint details from marker data
      const waypointDetails: WaypointDetailsProps = {
        command: 'WAYPOINT',
        frame: 'GLOBAL',
        param_1: 0,
        param_2: 0,
        param_3: 0,
        param_4: 0,
        latitude: marker.lat.toString(),
        longitude: marker.lng.toString(),
        altitude: '10.0',
      };

      setWaypointDetails(waypointDetails);
    },
    [],
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <MapForRouteUnified
        notUseActionButtons
        isLineMode={isLineMode}
        markerData={markerData.length > 0 ? markerData : []}
        style={{ height: '68rem' }}
        overlayContent={
          <WaypointDetails
            waypointDetails={waypointDetails}
            setWaypointDetails={setWaypointDetails}
          />
        }
        onMarkerClick={handleMarkerClick}
      />
    </div>
  );
};
