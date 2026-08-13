import { Box } from '@mui/material';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { BiExitFullscreen, BiFullscreen } from 'react-icons/bi';
import { FiMinus, FiPlus } from 'react-icons/fi';
import { IoLayersOutline } from 'react-icons/io5';
import { Map, MapMarker, Polyline } from 'react-kakao-maps-sdk';
import { useTheme } from 'rj-core';

import {
  getGeographicCenterAndZoomKakao,
  getGeographicCenterAndZoomKakaoByCenter,
} from '../../features/routes/utils/calculateCenterAndZoom';

export interface MarkerData {
  lat: number | string | null | undefined;
  lng: number | string | null | undefined;
  name?: string;
  icon?: string;
  terminal_name?: string;
}

export interface PolylinePath {
  lat: number | null | undefined;
  lng: number | null | undefined;
  for_robot?: boolean;
}

export interface MapBounds {
  sw: { lat: number; lng: number };
  ne: { lat: number; lng: number };
}

interface MapKakaoProps {
  centerTerminal?: { lat: number; lng: number } | null;
  level?: number;
  operatingMarkers?: MarkerData[];
  standbyMarkers?: MarkerData[];
  polylines?: Array<{
    route_terminals: Array<{
      lat: number | null | undefined;
      lng: number | null | undefined;
      for_robot?: boolean;
    }>;
    color: string;
  }>;
  style?: React.CSSProperties;
  overlayContent?: React.ReactNode;
  smallMarker?: boolean;
  bounds?: MapBounds;
  fitBounds?: boolean; // Auto-calculate and fit bounds from markers
  boundsPadding?: number; // Padding percentage for auto-calculated bounds (default: 0.1 = 10%)
  contentOverlay?: React.ReactNode;
  routeColor?: string;
  controlVisibility?: {
    [key: string]: boolean;
  };
}

type NormalizedMarkerData = MarkerData & { lat: number; lng: number };

const normalizeCoordinate = (
  value: number | string | null | undefined,
): number | null => {
  if (value === null || value === undefined) {
    return null;
  }
  const numericValue = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(numericValue)) {
    return null;
  }
  return numericValue;
};

const normalizeMarker = (marker: MarkerData): NormalizedMarkerData | null => {
  const lat = normalizeCoordinate(marker.lat);
  const lng = normalizeCoordinate(marker.lng);

  if (lat === null || lng === null || lat === 0 || lng === 0) {
    return null;
  }

  return {
    ...marker,
    lat,
    lng,
  };
};

const filterValidMarkers = (
  markers: MarkerData[] | undefined,
): NormalizedMarkerData[] => {
  return (markers ?? [])
    .map((marker) => normalizeMarker(marker))
    .filter((marker): marker is NormalizedMarkerData => marker !== null);
};

const createOffsetDrone = (
  width: number,
  height: number,
): { x: number; y: number } => {
  return {
    x: Math.round(width / 2),
    y: Math.round(height / 2),
  };
};

const createOffsetHouse = (
  width: number,
  height: number,
): { x: number; y: number } => {
  return {
    x: Math.round(width / 2),
    y: height,
  };
};

const overlayTypes = [
  'NONE',
  'TRAFFIC',
  'ROADVIEW',
  'TERRAIN',
  'USE_DISTRICT',
] as const;
type OverlayType = (typeof overlayTypes)[number];

const overlayMapTypeIdMap: Record<
  Exclude<OverlayType, 'NONE'>,
  | (typeof window.kakao.maps.MapTypeId)[keyof typeof window.kakao.maps.MapTypeId]
  | undefined
> = {
  TRAFFIC:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId?.TRAFFIC
      : undefined,
  ROADVIEW:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId?.ROADVIEW
      : undefined,
  TERRAIN:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId?.TERRAIN
      : undefined,
  USE_DISTRICT:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId?.USE_DISTRICT
      : undefined,
};

const MapKakaoAnYang = ({
  centerTerminal,
  operatingMarkers = [],
  standbyMarkers = [],
  polylines = [],
  style = {},
  overlayContent,
  smallMarker = false,
  controlVisibility,
  routeColor,
}: MapKakaoProps) => {
  const [theme] = useTheme();
  // const [mapTypeId, setMapTypeId] = React.useState<BaseMapType>("ROADMAP");
  const [overlayType, setOverlayType] = useState<OverlayType>('NONE');
  const [zoomLevel, setZoomLevel] = useState<number>(13);
  const [centerMap, setCenterMap] = useState<{ lat: number; lng: number }>({
    lat: 35.4152,
    lng: 127.5283,
  });

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [hasInitialized, setHasInitialized] = useState(false);
  const [mapReady, setMapReady] = useState(false);
  const internalMapRef = useRef<kakao.maps.Map | null>(null);

  // Memoize markers to prevent unnecessary recalculations
  const allMarkers = useMemo(() => {
    const operating = operatingMarkers || [];
    const standby = standbyMarkers || [];
    return [...operating, ...standby];
  }, [operatingMarkers, standbyMarkers]);

  // Memoize valid markers to prevent filtering on every render
  const validMarkers = useMemo<NormalizedMarkerData[]>(() => {
    return filterValidMarkers(allMarkers);
  }, [allMarkers]);

  const normalizedOperatingMarkers = useMemo<NormalizedMarkerData[]>(() => {
    return filterValidMarkers(operatingMarkers);
  }, [operatingMarkers]);

  const normalizedStandbyMarkers = useMemo<NormalizedMarkerData[]>(() => {
    return filterValidMarkers(standbyMarkers);
  }, [standbyMarkers]);

  // Reset initialization when markers change
  useEffect(() => {
    if (validMarkers.length > 0) {
      setHasInitialized(false);
    }
  }, [validMarkers.length]);

  // Check if Kakao SDK is loaded
  useEffect(() => {
    if (typeof kakao === 'undefined') {
      console.warn('Kakao SDK not loaded (Kakao servers may be down).');
      return;
    }
  }, []);

  // Handle map relayout on fullscreen change
  useEffect(() => {
    const map = internalMapRef.current;
    if (map && typeof map.relayout === 'function') {
      setTimeout(() => {
        map.relayout();
      }, 100);
    }
  }, [isFullscreen]);

  // Handle overlay type changes
  useEffect(() => {
    const map = internalMapRef.current;
    if (!map) return;
    Object.values(overlayMapTypeIdMap).forEach((typeId) => {
      if (typeId) map.removeOverlayMapTypeId(typeId);
    });
    if (
      overlayType !== 'NONE' &&
      overlayMapTypeIdMap[overlayType as Exclude<OverlayType, 'NONE'>]
    ) {
      map.addOverlayMapTypeId(
        overlayMapTypeIdMap[overlayType as Exclude<OverlayType, 'NONE'>],
      );
    }
  }, [overlayType]);

  useEffect(() => {
    if (!centerTerminal?.lat || !centerTerminal?.lng) {
      return;
    }
    const mapInstance = internalMapRef.current;
    if (!mapInstance || !mapReady) {
      return;
    }
    const { center: centerMapInstance, zoom } =
      getGeographicCenterAndZoomKakaoByCenter({
        stop: { lat: centerTerminal.lat, lng: centerTerminal.lng },
        map: mapInstance,
      });
    if (centerMapInstance && zoom) {
      setCenterMap({
        lat: centerMapInstance.getLat(),
        lng: centerMapInstance.getLng(),
      });
      setZoomLevel(zoom);
      setHasInitialized(true);
    }
  }, [centerTerminal, mapReady]);

  // Calculate center and zoom only when needed
  useEffect(() => {
    const mapInstance = internalMapRef.current;
    if (!mapInstance || hasInitialized || !mapReady) {
      return;
    }

    // If centerTerminal is provided, skip this effect (handled by centerTerminal effect)
    if (centerTerminal?.lat && centerTerminal?.lng) {
      return;
    }

    // If no valid markers, use default center
    if (validMarkers.length === 0) {
      setCenterMap({ lat: 37.5665, lng: 126.978 });
      setZoomLevel(13);
      setHasInitialized(true);
      return;
    }

    // If only one valid marker, center on it with appropriate zoom
    if (validMarkers.length === 1) {
      setCenterMap({
        lat: validMarkers[0].lat || 37.5665,
        lng: validMarkers[0].lng || 126.978,
      });
      setZoomLevel(10);
      setHasInitialized(true);
      return;
    }

    const terminalsForMap = validMarkers.map((terminal) => ({
      lat: terminal.lat,
      lng: terminal.lng,
    }));

    const { center, zoom } = getGeographicCenterAndZoomKakao({
      stops: terminalsForMap,
      map: mapInstance,
    });
    if (center && zoom) {
      // Ensure center is a plain object with lat/lng properties
      const centerObject =
        'getLat' in center && 'getLng' in center
          ? {
              lat: (center as { getLat: () => number }).getLat(),
              lng: (center as { getLng: () => number }).getLng(),
            }
          : center;
      setCenterMap(centerObject);
      setZoomLevel(zoom);
      setHasInitialized(true);
    }
  }, [
    validMarkers,
    hasInitialized,
    mapReady,
    centerTerminal,
    controlVisibility?.drone,
    controlVisibility?.house,
    controlVisibility?.route,
  ]);

  const handleToggleOverlay = useCallback(() => {
    setOverlayType((prev) => {
      const idx = overlayTypes.indexOf(prev);
      return overlayTypes[(idx + 1) % overlayTypes.length];
    });
  }, []);

  const handleZoomIn = useCallback(() => {
    if (internalMapRef.current) {
      const currentLevel = internalMapRef.current.getLevel();
      const newLevel = Math.max(1, currentLevel - 1);
      internalMapRef.current.setLevel(newLevel);
      setZoomLevel(newLevel);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (internalMapRef.current) {
      const currentLevel = internalMapRef.current.getLevel();
      const newLevel = Math.min(14, currentLevel + 1);
      internalMapRef.current.setLevel(newLevel);
      setZoomLevel(newLevel);
    }
  }, []);

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((f) => !f);
    setHasInitialized(false);
  }, []);

  // Handle map creation - this ensures we can calculate center after map is ready
  const handleMapCreate = useCallback((map: kakao.maps.Map) => {
    internalMapRef.current = map;
    setMapReady(true);
  }, []);

  // Memoize button styles to prevent recreation on every render
  const btnStyle = useMemo(
    () => ({
      background: theme === 'dark' ? '#2d2e30' : '#fff',
      border: `1px solid ${theme === 'dark' ? '#404040' : '#eee'}`,
      borderRadius: 8,
      padding: 6,
      cursor: 'pointer',
      boxShadow:
        theme === 'dark'
          ? '0 2px 8px rgba(0,0,0,0.3)'
          : '0 2px 8px rgba(0,0,0,0.08)',
      outline: 'none',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: theme === 'dark' ? '#ececef' : '#2D2E30',
    }),
    [theme],
  );

  return (
    <div
      style={{
        width: '100%',
        position: isFullscreen ? 'fixed' : 'relative',
        top: isFullscreen ? 0 : undefined,
        left: isFullscreen ? 0 : undefined,
        zIndex: isFullscreen ? 9999 : undefined,
        borderRadius: 8,
        ...style,
        height: isFullscreen ? '100vh' : style?.height || '500px',
      }}
    >
      {/* Controls: Zoom & Fullscreen */}
      <Box
        style={{
          position: 'absolute',
          top: 16,
          left: 16,
          zIndex: 250,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        <Box>
          <button
            onClick={handleZoomIn}
            style={{
              ...btnStyle,
              borderBottomLeftRadius: 0,
              borderBottomRightRadius: 0,
              borderBottom: 'none',
            }}
            type="button"
            title="Zoom in"
          >
            <FiPlus
              size={16}
              color={theme === 'dark' ? '#ececef' : '#2D2E30'}
            />
          </button>
          <button
            onClick={handleZoomOut}
            style={{
              ...btnStyle,
              borderTopLeftRadius: 0,
              borderTopRightRadius: 0,
              borderTop: 'none',
            }}
            type="button"
            title="Zoom out"
          >
            <FiMinus
              size={16}
              color={theme === 'dark' ? '#ececef' : '#2D2E30'}
            />
          </button>
        </Box>
        <button
          onClick={handleToggleFullscreen}
          style={{
            ...btnStyle,
            padding: 2,
          }}
          title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          type="button"
        >
          {isFullscreen ? (
            <BiExitFullscreen
              size={24}
              color={theme === 'dark' ? '#ececef' : '#2D2E30'}
            />
          ) : (
            <BiFullscreen
              size={24}
              color={theme === 'dark' ? '#ececef' : '#2D2E30'}
            />
          )}
        </button>
      </Box>
      {/* Toggle Overlay Map Type Button */}
      <div
        style={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 1000,
        }}
      >
        <div
          title={overlayType}
          style={{
            cursor: 'pointer',
            background: theme === 'dark' ? '#2d2e30' : '#fff',
            borderRadius: '0.5rem',
            padding: '0.5rem',
            boxShadow:
              theme === 'dark'
                ? '0 2px 8px rgba(0,0,0,0.3)'
                : '0 2px 8px rgba(0,0,0,0.15)',
            marginBottom: '0.5rem',
            border: `1px solid ${theme === 'dark' ? '#404040' : 'transparent'}`,
          }}
          onClick={handleToggleOverlay}
        >
          <IoLayersOutline
            size={24}
            color={theme === 'dark' ? '#ececef' : '#2D2E30'}
          />
        </div>
        {overlayContent}
      </div>
      <Map
        key={`map-${isFullscreen ? 'fullscreen' : 'normal'}-${theme}`}
        ref={internalMapRef}
        center={centerMap}
        level={zoomLevel}
        style={{
          width: '100%',
          height: '100%',
          borderRadius: 8,
          // Apply CSS filter for dark mode (similar to other map components in codebase)
          filter:
            theme === 'dark'
              ? 'invert(1.5) hue-rotate(180deg)'
              : 'invert(0) hue-rotate(0deg)',
        }}
        onCreate={handleMapCreate}
      >
        {/* Polyline paths */}
        {polylines.map(
          (path: { route_terminals: PolylinePath[]; color: string }, idx) => {
            // Filter valid points and convert to proper format
            const validPoints = path.route_terminals
              ?.filter(
                (point) =>
                  point.lat && point.lng && point.lat !== 0 && point.lng !== 0,
              )
              ?.map((point: PolylinePath) => ({
                lat: Number(point.lat),
                lng: Number(point.lng),
                for_robot: point.for_robot,
              }));

            if (validPoints.length < 2) return null;

            // Create polylines for each segment based on for_robot status
            const segments: Array<{
              points: Array<{ lat: number; lng: number; for_robot?: boolean }>;
              isRobotRoute: boolean;
            }> = [];

            // Process each pair of consecutive points
            for (let i = 0; i < validPoints.length - 1; i++) {
              const currentPoint = validPoints[i];
              const nextPoint = validPoints[i + 1];

              // Determine the color for this segment based on current point's robot status
              const isRobotRoute = currentPoint.for_robot || false;

              // Create segment from current point to next point
              const segment = {
                points: [
                  {
                    lat: currentPoint.lat,
                    lng: currentPoint.lng,
                    for_robot: currentPoint.for_robot,
                  },
                  {
                    lat: nextPoint.lat,
                    lng: nextPoint.lng,
                    for_robot: nextPoint.for_robot,
                  },
                ],
                isRobotRoute: isRobotRoute,
              };

              segments.push(segment);
            }

            return segments.map((segment, segmentIdx) => (
              <Polyline
                key={`polyline-${idx}-${segmentIdx}`}
                path={segment.points.map((p) => ({ lat: p.lat, lng: p.lng }))}
                strokeWeight={4}
                strokeColor={path.color} // Green for robot route, red for normal
                strokeOpacity={0.7}
                strokeStyle="solid"
              />
            ));
          },
        )}
        {/* Operating markers */}
        {normalizedOperatingMarkers.map((marker, idx) => {
          return marker.icon ? (
            <MapMarker
              key={'op-' + idx}
              position={{ lat: marker.lat, lng: marker.lng }}
              image={{
                src: marker.icon,
                size: { width: 40, height: 40 },
                options: {
                  offset:
                    marker.type === 'drone'
                      ? createOffsetDrone(40, 40)
                      : createOffsetHouse(40, 40),
                },
              }}
              title={marker.name || marker.terminal_name}
            />
          ) : smallMarker ? (
            <MapMarker
              key={'op-' + idx}
              position={{ lat: marker.lat, lng: marker.lng }}
              image={{
                src: "data:image/svg+xml;utf8,<svg width='16' height='16' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23fd0000'><path d='M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z'/></svg>",
                size: { width: 16, height: 16 },
                options: {
                  offset:
                    marker.type === 'drone'
                      ? createOffsetDrone(16, 16)
                      : createOffsetHouse(16, 16),
                },
              }}
              title={marker.name || marker.terminal_name}
            />
          ) : (
            <MapMarker
              key={'op-' + idx}
              position={{ lat: marker.lat, lng: marker.lng }}
              image={{
                src: `data:image/svg+xml;utf8,<svg width='32' height='32' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23${routeColor ? routeColor : 'fd0000'}' opacity='0.85'><path d='M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z'/></svg>`,
                size: { width: 32, height: 32 },
                options: {
                  offset:
                    marker.type === 'drone'
                      ? createOffsetDrone(32, 32)
                      : createOffsetHouse(32, 32),
                },
              }}
              title={marker.name || marker.terminal_name}
            />
          );
        })}
        {/* Standby markers */}
        {normalizedStandbyMarkers.map((marker, idx) =>
          smallMarker ? (
            <MapMarker
              key={'st-' + idx}
              position={{ lat: marker.lat, lng: marker.lng }}
              image={{
                src: "data:image/svg+xml;utf8,<svg width='16' height='16' xmlns='http://www.w3.org/2000/svg'><circle cx='8' cy='8' r='7' fill='%23e74c3c' stroke='white' stroke-width='2'/></svg>",
                size: { width: 16, height: 16 },
                options: {
                  offset:
                    marker.type === 'drone'
                      ? createOffsetDrone(16, 16)
                      : createOffsetHouse(16, 16),
                },
              }}
              title={marker.name || marker.terminal_name}
            />
          ) : (
            <MapMarker
              key={'st-' + idx}
              position={{ lat: marker.lat, lng: marker.lng }}
              image={{
                src: 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png',
                size: { width: 24, height: 35 },
                options: {
                  offset:
                    marker.type === 'drone'
                      ? createOffsetDrone(24, 35)
                      : createOffsetHouse(24, 35),
                },
              }}
              title={marker.name || marker.terminal_name}
            />
          ),
        )}
      </Map>
      {/* {overlayContent && (
        <div
          style={{
            position: 'absolute',
            top: 20,
            right: 20,
            background:
              theme === 'dark'
                ? 'rgba(45,46,48,0.95)'
                : 'rgba(255,255,255,0.9)',
            padding: 10,
            borderRadius: 5,
            zIndex: 1000,
            border: `1px solid ${theme === 'dark' ? '#232325' : '#e0e0e0'}`,
          }}
        >
          {overlayContent}
        </div>
      )} */}
    </div>
  );
};

export default React.memo(MapKakaoAnYang);
