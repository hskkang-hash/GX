import { Box } from '@mui/material';
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
import React, {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { IoLayersOutline } from 'react-icons/io5';
import { MdAddLocation, MdOutlineAddLocation } from 'react-icons/md';
import { useTheme } from 'rj-core';
import styled from 'styled-components';

import RouteIcon from '@/assets/images/RouteIcon.svg';

import { useZustandRoutes } from '../stores/useZustandRoutes';
import { getGeographicCenterAndZoomGoogle } from '../utils/calculateCenterAndZoom';

// Utility function to validate and normalize coordinates
const validateCoordinate = (
  value: number | string | undefined,
): number | null => {
  const num = typeof value === 'number' ? value : Number(value);
  return num && !isNaN(num) && num !== 0 ? num : null;
};

// Utility function to check if coordinates are valid
const isValidCoordinate = (
  lat: number | string | undefined,
  lng: number | string | undefined,
): boolean => {
  const latNum = validateCoordinate(lat);
  const lngNum = validateCoordinate(lng);
  return latNum !== null && lngNum !== null;
};

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

type Marker = {
  lat: number;
  lng: number;
  name?: string;
  for_robot?: boolean;
};

type Props = {
  routeGroups?: { name?: string; lat: number; lng: number }[][];
  markerData?: Marker[];
  height?: string;
  dronePosition?: {
    lat: number;
    lng: number;
  };
  iconDrone?: string;
  style?: React.CSSProperties;
  useAddLocation?: boolean;
  handleAddLocation?: (position: { lat: number; lng: number }) => void;
  getMapRef?: (map: google.maps.Map) => void;
  apiKey: string;
  onMarkerClick?: (marker: Marker) => void;
};

const mapTypes = ['roadmap', 'satellite', 'hybrid', 'terrain'] as const;
type MapType = (typeof mapTypes)[number];

// Polyline component for Google Maps
const GooglePolyline = React.memo(
  ({
    path,
    color,
    offset = 0,
  }: {
    path: { lat: number; lng: number }[];
    color: string;
    offset?: number;
  }) => {
    const map = useMap();
    const polylineRef = useRef<google.maps.Polyline | null>(null);

    useEffect(() => {
      if (!map) return;

      // Clean up existing polyline first
      const currentPolyline = polylineRef.current;
      if (currentPolyline) {
        currentPolyline.setMap(null);
        polylineRef.current = null;
      }

      // If no path or path is empty, don't create polyline
      if (!path || path.length === 0) {
        return;
      }

      // Apply offset to path and ensure valid coordinates
      const offsetPath = path
        .filter((point) => {
          const lat =
            typeof point.lat === 'number' ? point.lat : Number(point.lat);
          const lng =
            typeof point.lng === 'number' ? point.lng : Number(point.lng);
          return (
            lat && lng && !isNaN(lat) && !isNaN(lng) && lat !== 0 && lng !== 0
          );
        })
        .map((point) => {
          const lat =
            typeof point.lat === 'number' ? point.lat : Number(point.lat);
          const lng =
            typeof point.lng === 'number' ? point.lng : Number(point.lng);
          return {
            lat: lat + offset,
            lng: lng + offset,
          };
        });

      if (offsetPath.length < 2) return; // Need at least 2 points for a polyline

      // Create polyline
      const polyline = new google.maps.Polyline({
        path: offsetPath,
        geodesic: true,
        strokeColor: color,
        strokeOpacity: 0.7,
        strokeWeight: 4,
      });

      polyline.setMap(map);
      polylineRef.current = polyline;

      return () => {
        if (polylineRef.current) {
          polylineRef.current.setMap(null);
          polylineRef.current = null;
        }
      };
    }, [map, path, color, offset]);

    return null;
  },
);

// Individual polyline segment for markerData
const GooglePolylineSegment = ({
  start,
  end,
  isRobotRoute,
}: {
  start: { lat: number; lng: number };
  end: { lat: number; lng: number };
  isRobotRoute: boolean;
}) => {
  const map = useMap();
  const polylineRef = useRef<google.maps.Polyline | null>(null);

  useEffect(() => {
    if (!map) return;

    // Clean up existing polyline first
    const currentPolyline = polylineRef.current;
    if (currentPolyline) {
      currentPolyline.setMap(null);
      polylineRef.current = null;
    }

    // Validate coordinates
    const startLat =
      typeof start.lat === 'number' ? start.lat : Number(start.lat);
    const startLng =
      typeof start.lng === 'number' ? start.lng : Number(start.lng);
    const endLat = typeof end.lat === 'number' ? end.lat : Number(end.lat);
    const endLng = typeof end.lng === 'number' ? end.lng : Number(end.lng);

    if (
      !startLat ||
      !startLng ||
      !endLat ||
      !endLng ||
      isNaN(startLat) ||
      isNaN(startLng) ||
      isNaN(endLat) ||
      isNaN(endLng) ||
      startLat === 0 ||
      startLng === 0 ||
      endLat === 0 ||
      endLng === 0
    ) {
      return;
    }

    // Create polyline segment
    const polyline = new google.maps.Polyline({
      path: [
        { lat: startLat, lng: startLng },
        { lat: endLat, lng: endLng },
      ],
      geodesic: true,
      strokeColor: isRobotRoute ? '#22c55e' : '#0CBA47',
      strokeOpacity: 0.7,
      strokeWeight: 4,
    });

    polyline.setMap(map);
    polylineRef.current = polyline;

    return () => {
      if (polylineRef.current) {
        polylineRef.current.setMap(null);
        polylineRef.current = null;
      }
    };
  }, [map, start, end, isRobotRoute]);

  return null;
};

const MapForRouteGoogleContent = ({
  routeGroups = [],
  markerData = [],
  dronePosition,
  style = {},
  useAddLocation = false,
  handleAddLocation,
  getMapRef,
  onMarkerClick,
}: Omit<Props, 'apiKey'>) => {
  const [theme] = useTheme();
  const [mapType, setMapType] = useState<MapType>('roadmap');

  const [isAddLocation, setIsAddLocation] = useState(false);
  const map = useMap();
  const isUpdatingRef = useRef(false);
  const prevMarkerDataRef = useRef<Marker[]>([]);
  const [zoomLevel, setZoomLevel] = useState<number>(3);
  const [centerMap, setCenterMap] = useState({
    lat: 37.5665,
    lng: 126.978,
  });

  const { setCenterAndZoom } = useZustandRoutes();

  // Memoize filtered markers for better performance
  const filteredMarkerData = useMemo(
    () =>
      markerData.filter((marker) => isValidCoordinate(marker.lat, marker.lng)),
    [markerData],
  );

  // Pass map ref to parent if needed
  useEffect(() => {
    if (map && getMapRef) {
      getMapRef(map);
    }
  }, [map, getMapRef]);

  // Auto-center map based on marker data - only run when markers actually change
  const updateMapView = useCallback((): void => {
    if (isUpdatingRef.current) return;

    isUpdatingRef.current = true;

    // Check if we need to update the center/zoom to avoid unnecessary re-renders
    const currentCenter = centerMap;
    const currentZoom = zoomLevel;

    if (markerData.length === 1) {
      const lat = Number(markerData[0].lat) || 37.5665;
      const lng = Number(markerData[0].lng) || 126.978;

      // Only update if the center has actually changed
      if (
        Math.abs(currentCenter.lat - lat) > 0.0001 ||
        Math.abs(currentCenter.lng - lng) > 0.0001 ||
        currentZoom !== 10
      ) {
        setCenterMap({ lat, lng });
        setZoomLevel(10);
        setCenterAndZoom({ lat, lng }, 10);
      }
      isUpdatingRef.current = false;
      return;
    }

    // Use Google Maps equivalent of Kakao's center calculation
    const { center: calculatedCenter, zoom: calculatedZoom } =
      getGeographicCenterAndZoomGoogle({
        stops: markerData,
        map: map,
      });

    console.log('calculatedCenter', calculatedCenter);
    console.log('calculatedZoom', calculatedZoom);

    if (calculatedCenter && calculatedZoom) {
      // Only update if the center/zoom has actually changed
      if (
        Math.abs(currentCenter.lat - calculatedCenter.lat) > 0.0001 ||
        Math.abs(currentCenter.lng - calculatedCenter.lng) > 0.0001 ||
        Math.abs(currentZoom - calculatedZoom) > 0.1
      ) {
        setCenterMap(calculatedCenter);
        setZoomLevel(calculatedZoom);
        setCenterAndZoom(calculatedCenter, calculatedZoom);
      }
    }

    isUpdatingRef.current = false;
  }, [
    map,
    markerData,
    centerMap,
    zoomLevel,
    setCenterMap,
    setZoomLevel,
    setCenterAndZoom,
  ]);

  useEffect(() => {
    if (!map || !markerData || markerData.length === 0 || isUpdatingRef.current)
      return;

    // Check if markerData has actually changed
    const hasMarkerDataChanged =
      prevMarkerDataRef.current.length !== markerData.length ||
      prevMarkerDataRef.current.some((prevMarker, index) => {
        const currentMarker = markerData[index];
        return (
          !currentMarker ||
          prevMarker.lat !== currentMarker.lat ||
          prevMarker.lng !== currentMarker.lng
        );
      });

    if (!hasMarkerDataChanged) return;

    // Update the ref to track current markerData
    prevMarkerDataRef.current = [...markerData];

    // Use requestAnimationFrame for better performance than setTimeout
    const timeoutId = requestAnimationFrame(updateMapView);

    return () => {
      cancelAnimationFrame(timeoutId);
      isUpdatingRef.current = false;
    };
  }, [map, markerData, updateMapView]);

  const handleCameraChange = useCallback(
    (ev: MapCameraChangedEvent) => {
      setCenterMap(ev.detail.center);
      setZoomLevel(ev.detail.zoom);
    },
    [setCenterMap, setZoomLevel],
  );

  const handleToggleMapType = () => {
    setMapType((prev) => {
      const idx = mapTypes.indexOf(prev);
      return mapTypes[(idx + 1) % mapTypes.length];
    });
  };

  const handleToggleAddLocation = () => setIsAddLocation((prev) => !prev);

  const handleMapClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (event: any) => {
      if (!isAddLocation) {
        return;
      }

      let lat: number, lng: number;

      // Handle different event structures
      if (event.detail?.latLng) {
        // @vis.gl/react-google-maps event structure
        const latLng = event.detail.latLng;
        if (
          typeof latLng.lat === 'function' &&
          typeof latLng.lng === 'function'
        ) {
          lat = latLng.lat();
          lng = latLng.lng();
        } else if (
          typeof latLng.lat === 'number' &&
          typeof latLng.lng === 'number'
        ) {
          lat = latLng.lat;
          lng = latLng.lng;
        } else {
          return; // Invalid latLng structure
        }
      } else if (event.latLng) {
        // Standard Google Maps event structure
        const latLng = event.latLng;
        if (
          typeof latLng.lat === 'function' &&
          typeof latLng.lng === 'function'
        ) {
          lat = latLng.lat();
          lng = latLng.lng();
        } else if (
          typeof latLng.lat === 'number' &&
          typeof latLng.lng === 'number'
        ) {
          lat = latLng.lat;
          lng = latLng.lng;
        } else {
          return; // Invalid latLng structure
        }
      } else {
        return; // No valid coordinates found
      }

      // Validate coordinates
      if (!lat || !lng || isNaN(lat) || isNaN(lng) || lat === 0 || lng === 0) {
        return;
      }

      handleAddLocation?.({ lat, lng });
    },
    [isAddLocation, handleAddLocation],
  );

  const btnStyle = {
    background: theme === 'dark' ? 'rgb(68, 68, 68)' : '#fff',
    color: theme === 'dark' ? 'rgb(230, 230, 230)' : '#2D2E30',
    border: `1px solid ${theme === 'dark' ? 'rgb(68, 68, 68)' : '#eee'}`,
    borderRadius: 8,
    padding: 6,
    cursor: 'pointer',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    outline: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  return (
    <GoogleMapWrapper
      $isDark={theme === 'dark'}
      style={{
        width: '100%',
        position: 'relative',
        borderRadius: 8,
        ...style,
        height: style?.height || '500px',
      }}
    >
      {/* Toggle Overlay Map Type Button */}
      <Box
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        <Box>
          <button
            style={btnStyle}
            onClick={handleToggleMapType}
            title={mapType}
            type="button"
          >
            <IoLayersOutline
              size={20}
              color={theme === 'dark' ? 'rgb(230, 230, 230)' : '#2D2E30'}
            />
          </button>
        </Box>
        {useAddLocation && (
          <button
            onClick={handleToggleAddLocation}
            style={{
              ...btnStyle,
              borderColor: isAddLocation
                ? theme === 'dark'
                  ? '#fff'
                  : '#000'
                : theme === 'dark'
                  ? 'rgb(68, 68, 68)'
                  : '#eee',
            }}
            type="button"
            title={isAddLocation ? 'Exit add location' : 'Add location'}
          >
            {isAddLocation ? (
              <MdAddLocation
                size={20}
                color={theme === 'dark' ? 'rgb(230, 230, 230)' : '#2D2E30'}
              />
            ) : (
              <MdOutlineAddLocation
                size={20}
                color={theme === 'dark' ? 'rgb(230, 230, 230)' : '#2D2E30'}
              />
            )}
          </button>
        )}
      </Box>

      <Map
        center={centerMap}
        zoom={zoomLevel}
        mapTypeId={mapType}
        mapId="guardianx-route-map"
        style={{
          width: '100%',
          height: '100%',
          borderRadius: 8,
        }}
        onClick={handleMapClick}
        onCameraChanged={handleCameraChange}
        streetViewControl={false}
        fullscreenControl={true}
        fullscreenControlOptions={{
          position: ControlPosition.BOTTOM_LEFT,
        }}
        mapTypeControl={false}
        mapTypeControlOptions={{
          position: ControlPosition.TOP_RIGHT,
        }}
        cameraControl={true}
        cameraControlOptions={{
          position: ControlPosition.BOTTOM_RIGHT,
        }}
        zoomControl={true}
        zoomControlOptions={{
          position: ControlPosition.TOP_LEFT,
        }}
        keyboardShortcuts={false}
        colorScheme={theme === 'dark' ? ColorScheme.DARK : ColorScheme.LIGHT}
        gestureHandling="greedy"
      >
        {/* Route Groups - operating markers with blue color */}
        {routeGroups.map((route, groupIndex) => {
          const basePath = route
            .filter((marker) => isValidCoordinate(marker.lat, marker.lng))
            .map((marker) => ({
              lat: validateCoordinate(marker.lat)!,
              lng: validateCoordinate(marker.lng)!,
            }));

          return (
            <Fragment key={groupIndex}>
              {route
                .filter((marker) => isValidCoordinate(marker.lat, marker.lng))
                .map((marker, index) => {
                  const lat = validateCoordinate(marker.lat)!;
                  const lng = validateCoordinate(marker.lng)!;

                  const isSameAsDrone =
                    dronePosition &&
                    lat === dronePosition.lat &&
                    lng === dronePosition.lng;

                  if (isSameAsDrone) return null;

                  return (
                    <AdvancedMarker
                      key={`group-${groupIndex}-${index}`}
                      position={{ lat, lng }}
                      title={marker.name}
                    >
                      <Pin
                        background="#4169e1"
                        glyphColor="#ffffff"
                        borderColor="#ffffff"
                        scale={0.8}
                      />
                    </AdvancedMarker>
                  );
                })}
              {basePath.length >= 2 && (
                <GooglePolyline
                  path={basePath}
                  color={groupIndex === 0 ? '#FF0000' : '#0CBA47'}
                  offset={groupIndex === 1 ? 0.0005 : 0}
                />
              )}
            </Fragment>
          );
        })}

        {/* markerData - standby markers with red color */}
        {filteredMarkerData.map((marker, index) => {
          const lat = validateCoordinate(marker.lat)!;
          const lng = validateCoordinate(marker.lng)!;

          const isSameAsDrone =
            dronePosition &&
            lat === dronePosition.lat &&
            lng === dronePosition.lng;
          if (isSameAsDrone) return null;

          return (
            <AdvancedMarker
              key={`marker-${index}`}
              position={{ lat, lng }}
              title={marker.name}
              onClick={() => {
                if (onMarkerClick) {
                  onMarkerClick(marker);
                }
              }}
            >
              <img
                src={RouteIcon}
                alt={marker.name}
                style={{ width: 32, height: 32, cursor: 'pointer' }}
              />
            </AdvancedMarker>
          );
        })}

        {/* Polyline segments for markerData if more than 1 */}
        {filteredMarkerData.length >= 2 &&
          filteredMarkerData
            .filter((marker, index) => {
              if (index === filteredMarkerData.length - 1) return false; // Skip last marker
              const nextMarker = filteredMarkerData[index + 1];
              return (
                isValidCoordinate(marker.lat, marker.lng) &&
                isValidCoordinate(nextMarker.lat, nextMarker.lng)
              );
            })
            .map((marker, index) => {
              const nextMarker = filteredMarkerData[index + 1];
              const isRobotRoute = marker.for_robot; // only check the first point of the route

              const lat = validateCoordinate(marker.lat)!;
              const lng = validateCoordinate(marker.lng)!;
              const nextLat = validateCoordinate(nextMarker.lat)!;
              const nextLng = validateCoordinate(nextMarker.lng)!;

              return (
                <GooglePolylineSegment
                  key={`polyline-${index}`}
                  start={{ lat, lng }}
                  end={{ lat: nextLat, lng: nextLng }}
                  isRobotRoute={!!isRobotRoute}
                />
              );
            })}

        {/* Drone position marker (if any) */}
        {dronePosition &&
          isValidCoordinate(dronePosition.lat, dronePosition.lng) &&
          (() => {
            const lat = validateCoordinate(dronePosition.lat)!;
            const lng = validateCoordinate(dronePosition.lng)!;

            return (
              <AdvancedMarker
                position={{ lat, lng }}
                title="Drone"
              >
                <Pin
                  background="#FFD700"
                  glyphColor="#000000"
                  borderColor="#ffffff"
                  scale={1.4}
                />
              </AdvancedMarker>
            );
          })()}
      </Map>
    </GoogleMapWrapper>
  );
};

const MapForRouteGoogle = (props: Props) => {
  const { i18n } = useTranslation();
  const currentLanguage = i18n.language;

  return (
    <APIProvider
      apiKey={props.apiKey}
      language={currentLanguage === 'en' ? 'en' : 'ko'}
    >
      <MapForRouteGoogleContent {...props} />
    </APIProvider>
  );
};

export default React.memo(MapForRouteGoogle);
