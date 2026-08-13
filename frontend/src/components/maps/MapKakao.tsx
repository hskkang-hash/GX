import { Box } from '@mui/material';
import React, { useEffect, useRef, useState } from 'react';
import { BiExitFullscreen, BiFullscreen } from 'react-icons/bi';
import { FiMinus, FiPlus } from 'react-icons/fi';
import { IoLayersOutline } from 'react-icons/io5';
import { Map, MapMarker, Polyline } from 'react-kakao-maps-sdk';
import { useTheme } from 'rj-core';

import RouteIcon from '@/assets/images/RouteIcon.svg';

import { getGeographicCenterAndZoomKakao } from '../../features/routes/utils/calculateCenterAndZoom';

export interface MarkerData {
  lat: number | null | undefined;
  lng: number | null | undefined;
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
  centerTerminalZoom?: number;
  level?: number;
  operatingMarkers?: MarkerData[];
  standbyMarkers?: MarkerData[];
  droneMarkers?: MarkerData[];
  polylines?: PolylinePath[][];
  style?: React.CSSProperties;
  overlayContent?: React.ReactNode;
  smallMarker?: boolean;
  bounds?: MapBounds;
  fitBounds?: boolean; // Auto-calculate and fit bounds from markers
  boundsPadding?: number; // Padding percentage for auto-calculated bounds (default: 0.1 = 10%)
  contentOverlay?: React.ReactNode;
  routeColor?: string;
}

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

const MapKakao = ({
  centerTerminal,
  operatingMarkers = [],
  standbyMarkers = [],
  droneMarkers = [],
  polylines = [],
  style = {},
  overlayContent,
  smallMarker = false,
  centerTerminalZoom = 6,
  contentOverlay = null,
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
  const internalMapRef = useRef<kakao.maps.Map | null>(null);

  useEffect(() => {
    if (operatingMarkers && operatingMarkers.length > 0) {
      setHasInitialized(false);
    }
  }, [operatingMarkers]);

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

  // Calculate center and zoom only on initial render or when operatingMarkers change
  useEffect(() => {
    const map = internalMapRef.current;

    if (
      map &&
      operatingMarkers &&
      operatingMarkers.length > 0 &&
      !hasInitialized
    ) {
      setTimeout(() => {
        // Filter out markers with invalid coordinates (0,0)
        const validMarkers = operatingMarkers.filter(
          (terminal) =>
            terminal?.lat &&
            terminal?.lng &&
            terminal?.lat !== 0 &&
            terminal?.lng !== 0,
        );

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
          lat: terminal?.lat || 0,
          lng: terminal?.lng || 0,
        }));

        const { center, zoom } = getGeographicCenterAndZoomKakao({
          stops: terminalsForMap,
          map: internalMapRef.current,
        });
        if (center && zoom) {
          // Ensure center is a plain object with lat/lng properties
          const centerObject =
            typeof center === 'object' &&
            'getLat' in center &&
            'getLng' in center &&
            typeof (center as { getLat?: () => number }).getLat ===
              'function' &&
            typeof (center as { getLng?: () => number }).getLng === 'function'
              ? {
                  lat: (center as { getLat: () => number }).getLat(),
                  lng: (center as { getLng: () => number }).getLng(),
                }
              : (center as { lat: number; lng: number });
          setCenterMap(centerObject);
          setZoomLevel(zoom);
          setHasInitialized(true);
        }
      }, 200);
    }
  }, [operatingMarkers, hasInitialized]);

  useEffect(() => {
    if (centerTerminal?.lat && centerTerminal?.lng && internalMapRef.current) {
      const zoomLevel = centerTerminalZoom || 6;

      setCenterMap({
        lat: centerTerminal.lat,
        lng: centerTerminal.lng,
      });
      setZoomLevel(zoomLevel);
      setHasInitialized(true);

      const map = internalMapRef.current;
      if (map) {
        map.setCenter(
          new kakao.maps.LatLng(centerTerminal.lat, centerTerminal.lng),
        );
        map.setLevel(zoomLevel);
      }
    }
  }, [centerTerminal, centerTerminalZoom]);

  const handleToggleOverlay = () => {
    setOverlayType((prev) => {
      const idx = overlayTypes.indexOf(prev);
      return overlayTypes[(idx + 1) % overlayTypes.length];
    });
  };

  const handleZoomIn = () => {
    if (internalMapRef.current) {
      const currentLevel = internalMapRef.current.getLevel();
      const newLevel = Math.max(1, currentLevel - 1);
      internalMapRef.current.setLevel(newLevel);
      setZoomLevel(newLevel);
    }
  };

  const handleZoomOut = () => {
    if (internalMapRef.current) {
      const currentLevel = internalMapRef.current.getLevel();
      const newLevel = Math.min(14, currentLevel + 1);
      internalMapRef.current.setLevel(newLevel);
      setZoomLevel(newLevel);
    }
  };

  const handleToggleFullscreen = () => {
    setIsFullscreen((f) => !f);
    setHasInitialized(false);
  };

  const btnStyle = {
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
  };

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
          zIndex: 1000,
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
            border: `1px solid ${theme === 'dark' ? '#404040' : 'transparent'}`,
          }}
          onClick={handleToggleOverlay}
        >
          <IoLayersOutline
            size={24}
            color={theme === 'dark' ? '#ececef' : '#2D2E30'}
          />
        </div>
        {contentOverlay}
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
      >
        {/* Polyline paths */}
        {polylines.map((path, idx) => {
          // Filter valid points and convert to proper format
          const validPoints = path
            .filter(
              (point) =>
                point.lat && point.lng && point.lat !== 0 && point.lng !== 0,
            )
            .map((point) => ({
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
              strokeColor={segment.isRobotRoute ? '#22c55e' : '#0CBA47'} // Green for robot route, red for normal
              strokeOpacity={0.7}
              strokeStyle="solid"
            />
          ));
        })}
        {/* Operating markers */}
        {operatingMarkers
          .filter(
            (marker) =>
              marker?.lat &&
              marker?.lng &&
              marker?.lat !== 0 &&
              marker?.lng !== 0,
          )
          .map((marker, idx) => {
            return marker?.icon ? (
              <MapMarker
                key={'op-' + idx}
                position={{ lat: marker?.lat || 0, lng: marker?.lng || 0 }}
                zIndex={10}
                image={{
                  src: marker?.icon,
                  size: { width: 40, height: 40 },
                  options: {
                    offset: {
                      x: 20,
                      y: 40,
                    },
                  },
                }}
                title={marker?.name || marker?.terminal_name}
              />
            ) : smallMarker ? (
              <MapMarker
                key={'op-' + idx}
                position={{ lat: marker?.lat || 0, lng: marker?.lng || 0 }}
                image={{
                  src: RouteIcon,
                  size: { width: 16, height: 16 },
                  options: { offset: { x: 8, y: 16 } },
                }}
                title={marker?.name || marker?.terminal_name}
              />
            ) : (
              <MapMarker
                key={'op-' + idx}
                position={{ lat: marker?.lat || 0, lng: marker?.lng || 0 }}
                image={{
                  src: RouteIcon,
                  size: { width: 32, height: 32 },
                  options: { offset: { x: 16, y: 32 } },
                }}
                title={marker?.name || marker?.terminal_name}
              />
            );
          })}
        {/* Drone markers */}
        {droneMarkers
          .filter(
            (marker) =>
              marker?.lat &&
              marker?.lng &&
              marker?.lat !== 0 &&
              marker?.lng !== 0,
          )
          .map((marker, idx) => {
            const lat =
              typeof marker.lat === 'number'
                ? marker.lat
                : Number(marker.lat) || 0;
            const lng =
              typeof marker.lng === 'number'
                ? marker.lng
                : Number(marker.lng) || 0;
            return marker?.icon ? (
              <MapMarker
                key={'op-' + idx}
                position={{ lat, lng }}
                image={{
                  src: marker?.icon,
                  size: { width: 40, height: 40 },
                  options: { offset: { x: 20, y: 20 } },
                }}
                title={marker?.name || marker?.terminal_name}
              />
            ) : (
              <MapMarker
                key={'op-' + idx}
                position={{ lat: marker?.lat || 0, lng: marker?.lng || 0 }}
                image={{
                  src: 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png',
                  size: { width: 32, height: 32 },
                  options: { offset: { x: 16, y: 28 } },
                }}
                title={marker?.name || marker?.terminal_name}
              />
            );
          })}
        {/* Standby markers */}
        {standbyMarkers
          .filter(
            (marker) =>
              marker?.lat &&
              marker?.lng &&
              marker?.lat !== 0 &&
              marker?.lng !== 0,
          )
          .map((marker, idx) =>
            smallMarker ? (
              <MapMarker
                key={'st-' + idx}
                position={{ lat: marker?.lat || 0, lng: marker?.lng || 0 }}
                image={{
                  src: "data:image/svg+xml;utf8,<svg width='16' height='16' xmlns='http://www.w3.org/2000/svg'><circle cx='8' cy='8' r='7' fill='%23e74c3c' stroke='white' stroke-width='2'/></svg>",
                  size: { width: 16, height: 16 },
                  options: { offset: { x: 8, y: 8 } },
                }}
                title={marker?.name || marker?.terminal_name}
              />
            ) : (
              <MapMarker
                key={'st-' + idx}
                position={{ lat: marker?.lat || 0, lng: marker?.lng || 0 }}
                image={{
                  src: 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png',
                  size: { width: 24, height: 35 },
                  options: { offset: { x: 12, y: 35 } },
                }}
                title={marker?.name || marker?.terminal_name}
              />
            ),
          )}
      </Map>
      {overlayContent && (
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
      )}
    </div>
  );
};

export default React.memo(MapKakao);
