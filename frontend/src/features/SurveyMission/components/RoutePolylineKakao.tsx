import React, { useCallback, useMemo } from 'react';
import { MapMarker, Polyline } from 'react-kakao-maps-sdk';

interface Marker {
  lat: number;
  lng: number;
  name?: string;
  for_robot?: boolean;
  color?: string;
  routeId?: string | number;
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
}

const RoutePolylineKakao: React.FC<RoutePolylineKakaoProps> = ({
  markerData,
  strokeColor = '#ffffff',
  strokeWeight = 3,
  strokeOpacity = 0.8,
  strokeStyle = 'solid',
  isLineMode = false,
  onMarkerClick,
}) => {

  const path = useMemo(() => {
    return markerData
      .map((marker) => ({
        lat: marker.lat,
        lng: marker.lng,
      }))
      .filter((point) => {
        return Number.isFinite(point.lat) && Number.isFinite(point.lng);
      });
  }, [markerData]);

  const { segments, segmentColors } = useMemo(() => {
    if (path.length < 2) {
      return {
        segments: [] as Array<{
          startIndex: number;
          path: Array<{ lat: number; lng: number }>;
          color: string;
        }>,
        segmentColors: [] as (string | undefined)[],
      };
    }

    const resultSegments: Array<{
      startIndex: number;
      path: Array<{ lat: number; lng: number }>;
      color: string;
    }> = [];
    const colors: Array<string | undefined> = [];

    for (let index = 0; index < path.length - 1; index += 1) {
      const currentMarker = markerData[index];
      const nextMarker = markerData[index + 1];
      const currentRouteId = currentMarker?.routeId ?? '__default__';
      const nextRouteId = nextMarker?.routeId ?? currentRouteId;

      if (currentRouteId !== nextRouteId) {
        colors[index] = undefined;
        continue;
      }

      const segmentColor =
        currentMarker?.color || nextMarker?.color || strokeColor;

      resultSegments.push({
        startIndex: index,
        path: [path[index], path[index + 1]],
        color: segmentColor,
      });
      colors[index] = segmentColor;
    }

    return { segments: resultSegments, segmentColors: colors };
  }, [path, markerData, strokeColor]);

  const fallbackStrokeColor =
    segmentColors.find((color) => color && color.length > 0) ?? strokeColor;

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

  const arrowPositions = useMemo(() => {
    if (path.length < 2) {
      return [] as Array<{
        lat: number;
        lng: number;
        rotation: number;
        color: string;
      }>;
    }

    const count = Math.min(Math.max(2, Math.floor(path.length / 3)), 5);
    const stepValue = Math.max(1, Math.floor(path.length / (count + 1)));
    const positions: Array<{
      lat: number;
      lng: number;
      rotation: number;
      color: string;
    }> = [];

    for (let index = stepValue; index < path.length - 1; index += stepValue) {
      const segmentColor = segmentColors[index];
      if (!segmentColor) {
        continue;
      }

      const currentPoint = path[index];
      const nextPoint = path[index + 1];

      const midLat = (currentPoint.lat + nextPoint.lat) / 2;
      const midLng = (currentPoint.lng + nextPoint.lng) / 2;
      const rotation = calculateBearing(currentPoint, nextPoint);

      positions.push({
        lat: midLat,
        lng: midLng,
        rotation,
        color: segmentColor,
      });
    }

    return positions;
  }, [path, segmentColors, calculateBearing]);

  if (segments.length === 0) {
    return null;
  }

  return (
    <>
      {/* Main polylines segmented by marker color */}
      {segments.map((segment) => (
        <Polyline
          key={`polyline-segment-${segment.startIndex}-${strokeColor}`}
          path={segment.path}
          strokeWeight={strokeWeight}
          strokeColor={segment.color}
          strokeOpacity={strokeOpacity}
          strokeStyle={strokeStyle}
          zIndex={1}
        />
      ))}

      {isLineMode ? (
        /* For LINE mode: show markers for each point */
        path.map((point, index) => {
          const markerColor = markerData[index]?.color ?? fallbackStrokeColor;
          const markerTitle =
            markerData[index]?.name ?? `Waypoint ${index + 1}`;

          return (
            <MapMarker
              key={`point-${index}`}
              position={point}
              image={{
                src:
                  'data:image/svg+xml;base64,' +
                  btoa(`
                  <svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="8" cy="8" r="6" fill="${markerColor}" opacity="${strokeOpacity}" stroke="#ffffff" stroke-width="2"/>
                  </svg>
                `),
                size: { width: 16, height: 16 },
                options: { offset: { x: 8, y: 8 } },
              }}
              clickable={!!onMarkerClick}
              title={markerTitle}
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
        })
      ) : (
        <>
          {/* Start marker */}
          <MapMarker
            position={path[0]}
            image={{
              src:
                'data:image/svg+xml;base64,' +
                btoa(`
                <svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="10" cy="10" r="8" fill="${markerData[0]?.color ?? '#00ff00'}" stroke="#ffffff" stroke-width="2"/>
                </svg>
              `),
              size: { width: 20, height: 20 },
              options: { offset: { x: 10, y: 10 } },
            }}
            clickable={!!onMarkerClick}
            title={markerData[0]?.name ?? 'Start Point'}
            onClick={() => {
              if (onMarkerClick) {
                const originalMarker = markerData[0];
                if (originalMarker) {
                  onMarkerClick(originalMarker);
                }
              }
            }}
            zIndex={3}
          />

          {/* End marker */}
          <MapMarker
            position={path[path.length - 1]}
            image={{
              src:
                'data:image/svg+xml;base64,' +
                btoa(`
                <svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="10" cy="10" r="8" fill="${
                    markerData[markerData.length - 1]?.color ?? '#ff0000'
                  }" stroke="#ffffff" stroke-width="2"/>
                </svg>
              `),
              size: { width: 20, height: 20 },
              options: { offset: { x: 10, y: 10 } },
            }}
            clickable={!!onMarkerClick}
            title={markerData[markerData.length - 1]?.name ?? 'End Point'}
            onClick={() => {
              if (onMarkerClick) {
                const originalMarker = markerData[markerData.length - 1];
                if (originalMarker) {
                  onMarkerClick(originalMarker);
                }
              }
            }}
            zIndex={3}
          />

          {/* Arrow markers */}
          {arrowPositions.map((arrow, index) => (
            <MapMarker
              key={`arrow-${index}`}
              position={{ lat: arrow.lat, lng: arrow.lng }}
              image={{
                src:
                  'data:image/svg+xml;base64,' +
                  btoa(`
                  <svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <g transform="translate(10,10) rotate(${arrow.rotation}) translate(-10,-10)">
                      <path d="M10 2l-3 6h6l-3-6z" 
                            fill="${arrow.color}" 
                            opacity="${strokeOpacity}"
                            stroke="#ffffff" 
                            stroke-width="1.5"/>
                    </g>
                  </svg>
                `),
                size: { width: 20, height: 20 },
                options: {
                  offset: { x: 10, y: 10 },
                },
              }}
              clickable={false}
              zIndex={2}
            />
          ))}
        </>
      )}
    </>
  );
};

export default React.memo(RoutePolylineKakao);
