import {
  APIProvider,
  AdvancedMarker,
  ColorScheme,
  ControlPosition,
  Map,
  MapCameraChangedEvent,
  Pin,
  useMap,
} from '@vis.gl/react-google-maps';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';
import styled from 'styled-components';

import {
  getGeographicCenterAndZoomGoogle,
  getGeographicCenterAndZoomGoogleByCenter,
} from '../../features/routes/utils/calculateCenterAndZoom';
import { Polyline } from './PolylineGoogleMap';

const GoogleMapWrapper = styled.div<{ $isDark?: boolean }>`
  border-radius: 8px;
  .gmnoprint a,
  .gmnoprint span,
  .gm-style-cc {
    display: none;
  }
  .gmnoprint div {
    background: none !important;
  }
  .gm-style-mtc-bbw {
    font-size: 1rem !important;
    ul {
      border-radius: 0.5rem !important;
      top: 2.625rem !important;
      li {
        label {
          font-size: 1.125rem !important;
        }
      }
    }
    .gm-style-mtc:first-of-type > button {
      font-size: 1.25rem !important;
      height: 2.5rem !important;
      border-start-start-radius: 0.5rem !important;
      border-end-start-radius: 0.5rem !important;
    }
    .gm-style-mtc:last-of-type > button {
      font-size: 1.25rem !important;
      height: 2.5rem !important;
      border-start-end-radius: 0.5rem !important;
      border-end-end-radius: 0.5rem !important;
    }
  }
  .gm-control-active {
    padding: 0.5rem !important;
    width: 2.5rem !important;
    height: 2.5rem !important;
    border-radius: 0.5rem !important;
    img {
      width: 1.5rem !important;
      height: 1.5rem !important;
    }
  }

  div[data-testid='map'] {
    & > div {
      border-radius: 8px;
    }
  }

  /* InfoWindow Theme-aware Styling */
  .gm-style-iw {
    background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
    color: ${(props) => (props.$isDark ? '#f9fafb' : '#111827')} !important;
    border-radius: 8px !important;
    box-shadow: ${(props) =>
    props.$isDark
      ? '0 10px 25px rgba(0, 0, 0, 0.8), 0 4px 10px rgba(0, 0, 0, 0.6)'
      : '0 10px 25px rgba(0, 0, 0, 0.15), 0 4px 10px rgba(0, 0, 0, 0.1)'} !important;
    border: ${(props) =>
    props.$isDark ? '1px solid #374151' : '1px solid #e5e7eb'} !important;

    & .transit-container {
      background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
      color: ${(props) => (props.$isDark ? '#f9fafb' : '#111827')} !important;
      & div {
        background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
        color: ${(props) => (props.$isDark ? '#f9fafb' : '#111827')} !important;
      }
    }
    & .poi-info-window {
      background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
      color: ${(props) => (props.$isDark ? '#f9fafb' : '#111827')} !important;
      & div {
        background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
        color: ${(props) => (props.$isDark ? '#f9fafb' : '#111827')} !important;
      }
      & a {
        background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
      }
    }
  }

  .gm-style-iw-c {
    background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
    border-radius: 8px !important;
    padding: 12px !important;
  }

  .gm-style-iw-d {
    background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
    color: ${(props) => (props.$isDark ? '#f9fafb' : '#111827')} !important;
    overflow: hidden !important;
  }

  .gm-style-iw-t {
    background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
  }

  /* InfoWindow Close Button */
  .gm-ui-hover-effect {
    border-radius: 50% !important;
    opacity: ${(props) => (props.$isDark ? '0.9' : '0.8')} !important;

    &:hover {
      background-color: ${(props) =>
    props.$isDark ? '#4b5563' : '#e5e7eb'} !important;
      opacity: 1 !important;
    }
  }

  /* InfoWindow Content Text */
  .gm-style-iw-chr {
    color: ${(props) => (props.$isDark ? '#f9fafb' : '#111827')} !important;
  }

  /* InfoWindow Links */
  .gm-style-iw a {
    color: ${(props) => (props.$isDark ? '#60a5fa' : '#2563eb')} !important;

    &:hover {
      color: ${(props) => (props.$isDark ? '#93c5fd' : '#1d4ed8')} !important;
    }
  }

  /* InfoWindow Arrow/Tail */
  .gm-style-iw-tc::after {
    background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
    border-color: ${(props) =>
    props.$isDark ? '#374151' : '#e5e7eb'} !important;
  }
`;

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

interface MapGoogleProps {
  apiKey: string;
  centerTerminal?: { lat: number; lng: number } | null;
  center?: { lat: number; lng: number };
  level?: number;
  operatingMarkers?: MarkerData[];
  standbyMarkers?: MarkerData[];
  droneMarkers?: MarkerData[];
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
  fitBounds?: boolean;
  boundsPadding?: number;
  controlVisibility?: {
    [key: string]: boolean;
  };
  routeColor?: string;
}

const MapGoogleContent = ({
  centerTerminal,
  operatingMarkers = [],
  standbyMarkers = [],
  droneMarkers = [],
  polylines = [],
  style = {},
  overlayContent,
  smallMarker = false,
  controlVisibility = {
    drone: true,
    house: true,
    route: true,
  },
  routeColor = '#fc6703',
}: Omit<MapGoogleProps, 'apiKey'>) => {
  const [theme] = useTheme();
  const [zoom, setZoom] = useState<number>(13);
  const [center, setCenter] = useState<{ lat: number; lng: number }>({
    lat: 37.5665,
    lng: 126.978,
  });
  const [hasInitialized, setHasInitialized] = useState(false);
  const map = useMap();

  // Memoize markers to prevent unnecessary recalculations
  const allMarkers = useMemo(() => {
    const operating = operatingMarkers || [];
    const standby = standbyMarkers || [];
    const drone = droneMarkers || [];
    return [...operating, ...standby, ...drone];
  }, [operatingMarkers, standbyMarkers, droneMarkers]);

  // Memoize valid markers to prevent filtering on every render
  const validMarkers = useMemo(() => {
    return allMarkers.filter(
      (terminal) =>
        terminal?.lat &&
        terminal?.lng &&
        terminal?.lat !== 0 &&
        terminal?.lng !== 0,
    );
  }, [allMarkers]);

  // Memoize style object to prevent unnecessary re-renders
  const memoizedStyle = useMemo(
    () => ({
      width: '100%',
      position: 'relative' as const,
      borderRadius: 8,
      ...style,
      height: style?.height || '500px',
    }),
    [style],
  );

  // Reset initialization when markers change
  useEffect(() => {
    if (validMarkers.length > 0) {
      setHasInitialized(false);
    }
  }, [validMarkers.length]);

  // Handle center terminal
  useEffect(() => {
    if (centerTerminal?.lat && centerTerminal?.lng && map) {
      if (typeof getGeographicCenterAndZoomGoogleByCenter === 'function') {
        const { center: calculatedCenter, zoom: calculatedZoom } =
          getGeographicCenterAndZoomGoogleByCenter({
            stop: { lat: centerTerminal.lat, lng: centerTerminal.lng },
            map: map,
          });

        if (calculatedCenter && calculatedZoom) {
          setCenter(calculatedCenter);
          setZoom(calculatedZoom);
          setHasInitialized(true);
        }
      } else {
        setCenter({
          lat: centerTerminal.lat,
          lng: centerTerminal.lng,
        });
        setZoom(15);
        setHasInitialized(true);
      }
    }
  }, [centerTerminal, map]);

  // Calculate center and zoom based on markers - only when no external center is provided
  useEffect(() => {
    if (map && validMarkers.length > 0 && !hasInitialized) {
      setTimeout(() => {
        // If no valid markers, use default center
        if (validMarkers.length === 0) {
          setCenter({ lat: 37.5665, lng: 126.978 });
          setZoom(13);
          setHasInitialized(true);
          return;
        }

        // If only one valid marker, center on it with appropriate zoom
        if (validMarkers.length === 1) {
          setCenter({
            lat: validMarkers[0].lat || 37.5665,
            lng: validMarkers[0].lng || 126.978,
          });
          setZoom(10);
          setHasInitialized(true);
          return;
        }

        const terminalsForMap = validMarkers.map((terminal) => ({
          lat: terminal?.lat || 0,
          lng: terminal?.lng || 0,
        }));

        const { center, zoom } = getGeographicCenterAndZoomGoogle({
          stops: terminalsForMap,
          map: map,
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
          setCenter(centerObject);
          setZoom(zoom);
          setHasInitialized(true);
        }
      }, 200);
    }
  }, [
    map,
    validMarkers,
    hasInitialized,
    controlVisibility.drone,
    controlVisibility.house,
    controlVisibility.route,
  ]);

  const handleCameraChange = useCallback((ev: MapCameraChangedEvent) => {
    setCenter(ev.detail.center);
    setZoom(ev.detail.zoom);
    // Trigger interaction callback when camera changes (user pan/zoom)
  }, []);

  return (
    <GoogleMapWrapper
      $isDark={theme === 'dark'}
      style={memoizedStyle}
    >
      <Map
        center={center}
        zoom={zoom}
        mapId="guardianx-map" // Required for Advanced Markers
        style={{
          width: '100%',
          height: '100%',
          borderRadius: 8,
        }}
        onCameraChanged={handleCameraChange}
        streetViewControl={false}
        fullscreenControl={true}
        fullscreenControlOptions={{
          position: ControlPosition.BOTTOM_LEFT,
        }}
        mapTypeControl={true}
        mapTypeControlOptions={{
          position: ControlPosition.TOP_RIGHT,
        }}
        zoomControl={true}
        zoomControlOptions={{
          position: ControlPosition.TOP_LEFT,
        }}
        keyboardShortcuts={false}
        colorScheme={theme === 'dark' ? ColorScheme.DARK : ColorScheme.LIGHT}
        gestureHandling="greedy"
      >
        {/* Markers */}
        {droneMarkers
          .filter((marker) => {
            const lat =
              typeof marker.lat === 'number' ? marker.lat : Number(marker.lat);
            const lng =
              typeof marker.lng === 'number' ? marker.lng : Number(marker.lng);
            return (
              lat && lng && lat !== 0 && lng !== 0 && !isNaN(lat) && !isNaN(lng)
            );
          })
          .map((marker, idx) => {
            const lat =
              typeof marker.lat === 'number'
                ? marker.lat
                : Number(marker.lat) || 0;
            const lng =
              typeof marker.lng === 'number'
                ? marker.lng
                : Number(marker.lng) || 0;
            return (
              <AdvancedMarker
                key={`drone-${idx}`}
                position={{ lat, lng }}
                title={marker.name || marker.terminal_name}
                zIndex={9999} // Maximum z-index to ensure drones appear above everything
              >
                {marker.icon ? (
                  <img
                    src={marker.icon}
                    alt={marker.name || marker.terminal_name}
                    width={40}
                    height={40}
                  />
                ) : (
                  <Pin
                    background="#22c55e"
                    glyphColor="#ffffff"
                    borderColor="#ffffff"
                    scale={smallMarker ? 0.8 : 1.2}
                  />
                )}
              </AdvancedMarker>
            );
          })}

        {/* Operating markers - clustered */}
        {operatingMarkers
          .filter((marker) => {
            const lat =
              typeof marker.lat === 'number' ? marker.lat : Number(marker.lat);
            const lng =
              typeof marker.lng === 'number' ? marker.lng : Number(marker.lng);
            return (
              lat && lng && lat !== 0 && lng !== 0 && !isNaN(lat) && !isNaN(lng)
            );
          })
          .map((marker, idx) => {
            const lat =
              typeof marker.lat === 'number'
                ? marker.lat
                : Number(marker.lat) || 0;
            const lng =
              typeof marker.lng === 'number'
                ? marker.lng
                : Number(marker.lng) || 0;
            return (
              <AdvancedMarker
                key={`op-${idx}`}
                position={{ lat, lng }}
                title={marker.name || marker.terminal_name}
              >
                {marker.icon ? (
                  <img
                    src={marker.icon}
                    alt={marker.name || marker.terminal_name}
                    width={40}
                    height={40}
                  />
                ) : (
                  <Pin
                    background={routeColor}
                    borderColor={routeColor}
                    scale={smallMarker ? 0.6 : 1.0}
                  />
                )}
              </AdvancedMarker>
            );
          })}

        {/* Standby markers - clustered */}
        {standbyMarkers
          .filter((marker) => {
            const lat =
              typeof marker.lat === 'number' ? marker.lat : Number(marker.lat);
            const lng =
              typeof marker.lng === 'number' ? marker.lng : Number(marker.lng);
            return (
              lat && lng && lat !== 0 && lng !== 0 && !isNaN(lat) && !isNaN(lng)
            );
          })
          .map((marker, idx) => {
            const lat =
              typeof marker.lat === 'number'
                ? marker.lat
                : Number(marker.lat) || 0;
            const lng =
              typeof marker.lng === 'number'
                ? marker.lng
                : Number(marker.lng) || 0;
            return (
              <AdvancedMarker
                key={`st-${idx}`}
                position={{ lat, lng }}
                title={marker.name || marker.terminal_name}
              >
                <Pin
                  background="#e74c3c"
                  glyphColor="#ffffff"
                  borderColor={theme === 'dark' ? '#1f2937' : '#ffffff'}
                  scale={smallMarker ? 0.6 : 1.0}
                />
              </AdvancedMarker>
            );
          })}

        {/* Polylines */}
        {polylines.map((path) => {
          // Filter valid points and convert to proper format
          const validPoints = path?.route_terminals
            ?.filter(
              (point) =>
                point.lat && point.lng && point.lat !== 0 && point.lng !== 0,
            )
            ?.map((point) => ({
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
              key={`polyline-${segmentIdx}`}
              path={segment.points.map((p) => ({ lat: p.lat, lng: p.lng }))}
              strokeColor={path.color}
              strokeOpacity={0.9}
              strokeWeight={5}
            />
          ));
        })}
      </Map>

      {overlayContent && (
        <div
          style={{
            position: 'absolute',
            top: 52,
            right: 8,
            padding: 10,
            borderRadius: 5,
            zIndex: 1000,
          }}
        >
          {overlayContent}
        </div>
      )}
    </GoogleMapWrapper>
  );
};

const MapGoogle = (props: MapGoogleProps) => {
  const { i18n } = useTranslation();
  const currentLanguage = i18n.language;

  return (
    <APIProvider
      apiKey={props.apiKey}
      language={
        currentLanguage === 'en' ? 'en' : currentLanguage === 'th' ? 'th' : 'ko'
      }
      region={
        currentLanguage === 'en' ? 'EN' : currentLanguage === 'th' ? 'TH' : 'KO'
      }
    >
      <MapGoogleContent {...props} />
    </APIProvider>
  );
};

export default React.memo(MapGoogle);
