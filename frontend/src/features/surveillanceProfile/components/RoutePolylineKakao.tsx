import React, { useCallback, useMemo } from 'react';
import { MapMarker, Polyline } from 'react-kakao-maps-sdk';

interface Marker {
  lat: number;
  lng: number;
  name?: string;
  for_robot?: boolean;
}

interface DroneRoute {
  route_path?: Array<{
    latitude: number;
    longitude: number;
    name?: string;
  }>;
  device?: {
    id: number;
    name: string;
    color?: string;
  };
}

interface RoutePolylineKakaoProps {
  markerData: Marker[];
  strokeColor?: string;
  strokeWeight?: number;
  strokeOpacity?: number;
  strokeStyle?:
  | 'solid'
  | 'shortdash'
  | 'shortdot'
  | 'shortdashdot'
  | 'shortdashdotdot'
  | 'dot'
  | 'dash'
  | 'longdash'
  | 'dashdot'
  | 'longdashdot'
  | 'longdashdotdot';
  isLineMode?: boolean;
  onMarkerClick?: (marker: Marker) => void;
  droneRoutes?: DroneRoute[];
}

// Helper function to create pin icon SVG (similar to Google Maps pin)
const createLocationPinIcon = (
  fillColor: string,
  scale: number,
): string => {
  const pinPath =
    'M 0,0 C -2,-10 -10,-12 -10,-20 A 10,10 0 1,1 10,-20 C 10,-12 2,-10 0,0 z M -2,-20 A 2,2 0 1,1 2,-20 2,2 0 1,1 -2,-20 z';

  const viewBoxSize = 40;
  const scaledSize = viewBoxSize * scale;
  const centerX = viewBoxSize / 2;
  const bottomY = viewBoxSize;

  return btoa(`
    <svg width="${scaledSize}" height="${scaledSize}" viewBox="0 0 ${viewBoxSize} ${viewBoxSize}" xmlns="http://www.w3.org/2000/svg">
      <g transform="translate(${centerX},${bottomY})">
        <path d="${pinPath}" 
              fill="${fillColor}" 
              fill-opacity="1"
              stroke="#ffffff" 
              stroke-width="2"/>
      </g>
    </svg>
  `);
};

const RoutePolylineKakao: React.FC<RoutePolylineKakaoProps> = ({
  markerData,
  strokeColor = '#2378d9',
  strokeWeight = 3,
  strokeOpacity = 0.8,
  strokeStyle = 'solid',
  isLineMode = false,
  onMarkerClick,
  droneRoutes = [],
}) => {

  if (!markerData || markerData.length < 2) {
    return null;
  }

  // Handle comma decimal separators and filter out invalid coordinates
  const path = markerData
    .map((marker) => {
      // Convert comma decimal separators to dots and parse as numbers
      const lat = Number(String(marker.lat).replace(',', '.'));
      const lng = Number(String(marker.lng).replace(',', '.'));
      return { lat, lng };
    })
    .filter((point) => {
      // Filter out invalid coordinates (NaN, 0,0, or out of valid range)
      return (
        !isNaN(point.lat) &&
        !isNaN(point.lng) &&
        !(point.lat === 0 && point.lng === 0) &&
        point.lat >= -90 &&
        point.lat <= 90 &&
        point.lng >= -180 &&
        point.lng <= 180
      );
    });

  if (path.length < 2) {
    return null;
  }

  // Helper function to calculate bearing between two points 
  const calculateBearing = useCallback(
    (
      from: { lat: number; lng: number },
      to: { lat: number; lng: number },
    ): number => {
      const lat1 = (from.lat * Math.PI) / 180;
      const lat2 = (to.lat * Math.PI) / 180;
      const deltaLng = ((to.lng - from.lng) * Math.PI) / 180;

      const y = Math.sin(deltaLng) * Math.cos(lat2);
      const x =
        Math.cos(lat1) * Math.sin(lat2) -
        Math.sin(lat1) * Math.cos(lat2) * Math.cos(deltaLng);

      return (Math.atan2(y, x) * 180) / Math.PI;
    },
    [],
  );

  // Generate arrow positions along the path 
  const arrowCount = Math.min(Math.max(2, Math.floor(path.length / 3)), 5); // 2-5 arrows like Google Maps
  const step = Math.max(1, Math.floor(path.length / (arrowCount + 1)));
  const arrowPositions: { lat: number; lng: number; rotation: number }[] = [];

  for (let i = step; i < path.length - 1; i += step) {
    const currentPoint = path[i];
    const nextPoint = path[i + 1];

    // Calculate midpoint between current and next point
    const midLat = (currentPoint.lat + nextPoint.lat) / 2;
    const midLng = (currentPoint.lng + nextPoint.lng) / 2;

    const bearing = calculateBearing(currentPoint, nextPoint);

    arrowPositions.push({
      lat: midLat,
      lng: midLng,
      rotation: bearing,
    });
  }

  // Process drone routes
  const droneRoutesData = useMemo(() => {
    return droneRoutes
      .map((droneRoute) => {
        if (!droneRoute.route_path || droneRoute.route_path.length < 1) {
          return null;
        }

        const dronePath = droneRoute.route_path
          .map((point) => ({
            lat: Number(point?.lat || 0),
            lng: Number(point?.lng || 0),
            name: point?.name || "WAYPOINT",
            altitude: point?.altitude ?? 0,
            command: point?.command ?? "WAYPOINT",
            frame: point?.frame ?? "FRAME",
            param_1: point?.param_1 ?? 0,
            param_2: point?.param_2 ?? 0,
            param_3: point?.param_3 ?? 0,
            param_4: point?.param_4 ?? 0,
          }))
          .filter((point) => {
            // Filter out invalid coordinates
            return (
              !isNaN(point.lat) &&
              !isNaN(point.lng) &&
              !(point.lat === 0 && point.lng === 0) &&
              point.lat >= -90 &&
              point.lat <= 90 &&
              point.lng >= -180 &&
              point.lng <= 180
            );
          });

        if (dronePath.length < 1) {
          return null;
        }

        return {
          path: dronePath,
          color: droneRoute.device?.color || '#ce0ef0',
        };
      })
      .filter((route) => route !== null) as Array<{
        path: Array<{ lat: number; lng: number; name?: string }>;
        color: string;
      }>;
  }, [droneRoutes]);

  return (
    <>
      {/* Main polyline */}
      <Polyline
        path={path}
        strokeWeight={strokeWeight}
        strokeColor={strokeColor}
        strokeOpacity={strokeOpacity}
        strokeStyle={strokeStyle}
        zIndex={1}
      />

      {isLineMode ? (
        /* For LINE mode: show pin markers for each point */
        path.map((point, index) => {
          const isStart = index === 0;
          const isEnd = index === path.length - 1;
          let fillColor = strokeColor;
          let scale = 1;

          if (isStart) {
            fillColor = '#00ff00';
            scale = 1.2;
          } else if (isEnd) {
            fillColor = '#ff0000';
            scale = 1.2;
          }

          const iconSize = 40 * scale;

          return (
            <MapMarker
              key={`point-${index}`}
              position={point}
              image={{
                src: `data:image/svg+xml;base64,${createLocationPinIcon(fillColor, scale)}`,
                size: { width: iconSize, height: iconSize },
                options: { offset: { x: iconSize / 2, y: iconSize } },
              }}
              clickable={!!onMarkerClick}
              title={isStart ? 'Start Point' : isEnd ? 'End Point' : `Waypoint ${index + 1}`}
              onClick={() => {
                if (onMarkerClick) {
                  const originalMarker = markerData[index];
                  if (originalMarker) {
                    onMarkerClick(originalMarker);
                  }
                }
              }}
              zIndex={2}
            />
          );
        })
      ) : (
        <>
          {/* Create markers for all waypoints (like Google Maps) */}
          {path.map((point, index) => {
            const isStart = index === 0;
            const isEnd = index === path.length - 1;

            let fillColor = strokeColor;
            let scale = 1;

            if (isStart) {
              fillColor = '#00ff00';
              scale = 1.2;
            } else if (isEnd) {
              fillColor = '#ff0000';
              scale = 1.2;
            }

            const iconSize = 40 * scale;

            return (
              <MapMarker
                key={`waypoint-${index}`}
                position={point}
                image={{
                  src: `data:image/svg+xml;base64,${createLocationPinIcon(fillColor, scale)}`,
                  size: { width: iconSize, height: iconSize },
                  options: { offset: { x: iconSize / 2, y: iconSize } },
                }}
                clickable={!!onMarkerClick}
                title={isStart ? 'Start Point' : isEnd ? 'End Point' : `Waypoint ${index + 1}`}
                onClick={() => {
                  if (onMarkerClick) {
                    const originalMarker = markerData[index];
                    if (originalMarker) {
                      onMarkerClick(originalMarker);
                    }
                  }
                }}
                zIndex={3}
              />
            );
          })}

          {/* Arrow markers */}
          {arrowPositions.map((arrow, index) => (
            <MapMarker
              key={`arrow-${index}`}
              position={{ lat: arrow.lat, lng: arrow.lng }}
              image={{
                src:
                  'data:image/svg+xml;base64,' +
                  btoa(`
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 512 512">
            <g transform="translate(256,256) rotate(${arrow.rotation}) translate(-256,-256)">
              <path
                d="M256 32 L480 480 L256 384 L32 480 Z"
                fill="${strokeColor}"
                stroke="${strokeColor}"
                stroke-width="30"
                stroke-linejoin="round"
                stroke-linecap="round"
              />
            </g>
          </svg>
        `),
                size: { width: 20, height: 20 },
                options: { offset: { x: 10, y: 10 } },
              }}
              clickable={false}
              zIndex={3}
            />
          ))}

        </>
      )}

      {/* Draw polyline and markers for each drone route */}
      {droneRoutesData.map((droneRoute, routeIndex) => (
        <React.Fragment key={`drone-route-${routeIndex}`}>
          <Polyline
            path={droneRoute.path}
            strokeWeight={strokeWeight + 1}
            strokeColor={droneRoute.color}
            strokeOpacity={strokeOpacity}
            strokeStyle={strokeStyle}
            zIndex={7}
          />
          {droneRoute.path.map((point, pointIndex) => {
            const iconSize = 40;
            return (
              <MapMarker
                key={`drone-marker-${routeIndex}-${pointIndex}`}
                position={point}
                image={{
                  src: `data:image/svg+xml;base64,${createLocationPinIcon(droneRoute.color, 1)}`,
                  size: { width: iconSize, height: iconSize },
                  options: { offset: { x: iconSize / 2, y: iconSize } },
                }}
                clickable={!!onMarkerClick}
                title={point.name || `Waypoint ${pointIndex + 1}`}
                onClick={() => {
                  if (onMarkerClick) {
                    const markerData: Marker = {
                      lat: point?.lat || 0,
                      lng: point?.lng || 0,
                      name: point?.name || `Waypoint ${pointIndex + 1}`,
                      command: point?.command ?? "WAYPOINT",
                      frame: point?.frame ?? "FRAME",
                      param_1: point?.param_1 ?? 0,
                      param_2: point?.param_2 ?? 0,
                      param_3: point?.param_3 ?? 0,
                      param_4: point?.param_4 ?? 0,
                      altitude: point?.altitude ?? 0,
                    };
                    onMarkerClick(markerData);
                  }
                }}
                zIndex={100}
              />
            );
          })}
        </React.Fragment>
      ))}
    </>
  );
};

export default React.memo(RoutePolylineKakao);
