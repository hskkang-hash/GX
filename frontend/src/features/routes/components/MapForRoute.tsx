import { Box } from '@mui/material';
import React, {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { BiExitFullscreen, BiFullscreen } from 'react-icons/bi';
import { FiMinus, FiPlus } from 'react-icons/fi';
import { IoLayersOutline } from 'react-icons/io5';
import { MdAddLocation, MdOutlineAddLocation } from 'react-icons/md';
import { Map, MapMarker, Polyline } from 'react-kakao-maps-sdk';
import { useTheme } from 'rj-core';

import RouteIcon from '@/assets/images/RouteIcon.svg';

import { useZustandRoutes } from '../stores/useZustandRoutes';
import { getGeographicCenterAndZoomKakao } from '../utils/calculateCenterAndZoom';

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

type Marker = {
  lat: number;
  lng: number;
  name?: string;
  for_robot?: boolean;
  color?: string;
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
  getMapRef?: (map: kakao.maps.Map) => void;
  onMarkerClick?: (marker: Marker) => void;
};

const overlayTypes = [
  'NONE',
  'TRAFFIC',
  'ROADVIEW',
  'TERRAIN',
  'USE_DISTRICT',
  'ROADMAP',
  'SKYVIEW',
  'HYBRID',
  'OVERLAY',
  'BICYCLE',
  'BICYCLE_HYBRID',
] as const;

type OverlayType = (typeof overlayTypes)[number];

const btnStyle = {
  background: '#fff',
  border: '1px solid #eee',
  borderRadius: 8,
  padding: 6,
  cursor: 'pointer',
  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  outline: 'none',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const overlayMapTypeIdMap: Record<
  Exclude<OverlayType, 'NONE'>,
  kakao.maps.MapTypeId | undefined
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
  ROADMAP:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId?.ROADMAP
      : undefined,
  SKYVIEW:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId?.SKYVIEW
      : undefined,
  HYBRID:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId?.HYBRID
      : undefined,
  OVERLAY:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId?.OVERLAY
      : undefined,
  BICYCLE:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId?.BICYCLE
      : undefined,
  BICYCLE_HYBRID:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId?.BICYCLE_HYBRID
      : undefined,
};

const MapForRoute = ({
  routeGroups = [],
  markerData = [],
  dronePosition,
  style = {},
  useAddLocation = false,
  handleAddLocation,
  onMarkerClick,
}: Props) => {
  const mapRef = useRef<kakao.maps.Map | null>(null);
  const isUpdatingRef = useRef(false);
  const prevMarkerDataRef = useRef<Marker[]>([]);
  const [theme] = useTheme();
  const [overlayType, setOverlayType] = useState<OverlayType>('NONE');
  const [zoomLevel, setZoomLevel] = useState<number>(3);
  const [centerMap, setCenterMap] = useState({
    lat: 37.5665,
    lng: 126.978,
  });

  const { setCenterAndZoom } = useZustandRoutes();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isAddLocation, setIsAddLocation] = useState(false);
  const [mapReady, setMapReady] = useState(false);

  // Memoize filtered markers for better performance
  const filteredMarkerData = useMemo(
    () =>
      markerData.filter((marker) => isValidCoordinate(marker.lat, marker.lng)),
    [markerData],
  );

  const offsetPath = (path: { lat: number; lng: number }[], offset = 0.0001) =>
    path.map((point) => ({
      lat: point.lat + offset,
      lng: point.lng + offset,
    }));

  useEffect(() => {
    if (typeof kakao === 'undefined') {
      console.warn('Kakao SDK not loaded (Kakao servers may be down).');
      return;
    }
  }, []);

  // Auto-center map based on marker data - only run when markers actually change
  const updateMapView = useCallback((): void => {
    if (isUpdatingRef.current || !mapRef.current || !mapReady) return;

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

    // Use Kakao Maps center calculation
    const terminalsForMap = markerData.map((terminal) => ({
      lat: terminal.lat,
      lng: terminal.lng,
    }));

    const { center, zoom } = getGeographicCenterAndZoomKakao({
      stops: terminalsForMap,
      map: mapRef.current as kakao.maps.Map,
    });

    if (center && zoom) {
      const newCenter = center as { lat: number; lng: number };

      // Only update if the center/zoom has actually changed
      if (
        Math.abs(currentCenter.lat - newCenter.lat) > 0.0001 ||
        Math.abs(currentCenter.lng - newCenter.lng) > 0.0001 ||
        Math.abs(currentZoom - zoom) > 0.1
      ) {
        setCenterMap(newCenter);
        setZoomLevel(zoom);
        setCenterAndZoom(newCenter, zoom);
      }
    }

    isUpdatingRef.current = false;
  }, [
    markerData,
    centerMap,
    zoomLevel,
    setCenterMap,
    setZoomLevel,
    setCenterAndZoom,
    mapReady,
  ]);

  // Trigger updateMapView when map becomes ready
  useEffect(() => {
    if (mapReady && markerData && markerData.length > 0) {
      // Reset prevMarkerDataRef to force update on first map ready
      prevMarkerDataRef.current = [];
      updateMapView();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapReady]); // Only trigger when map becomes ready, markerData changes are handled by the other useEffect

  useEffect(() => {
    if (
      !markerData ||
      markerData.length === 0 ||
      isUpdatingRef.current ||
      !mapReady
    )
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
  }, [markerData, updateMapView, mapReady]);

  const smallMarkerImage = (color: string) => ({
    src: `data:image/svg+xml;utf8,<svg width='16' height='16' xmlns='http://www.w3.org/2000/svg'><circle cx='8' cy='8' r='7' fill='${encodeURIComponent(
      color,
    )}' stroke='white' stroke-width='2'/></svg>`,
    size: { width: 16, height: 16 },
    options: { offset: { x: 8, y: 8 } },
  });

  // Zoom controls
  const handleZoomIn = useCallback(() => {
    if (mapRef.current) {
      const currentLevel = mapRef.current.getLevel();
      const newLevel = Math.max(1, currentLevel - 1);
      mapRef.current.setLevel(newLevel);

      setZoomLevel(newLevel);
    }
  }, [setZoomLevel]);
  const handleZoomOut = useCallback(() => {
    if (mapRef.current) {
      const currentLevel = mapRef.current.getLevel();
      const newLevel = Math.min(14, currentLevel + 1);
      mapRef.current.setLevel(newLevel);
      setZoomLevel(newLevel);
    }
  }, [setZoomLevel]);

  const handleToggleFullscreen = () => setIsFullscreen((f) => !f);

  const handleToggleAddLocation = () => setIsAddLocation((prev) => !prev);

  // Toggle overlay type
  const handleToggleOverlay = () => {
    setOverlayType((prev) => {
      const idx = overlayTypes.indexOf(prev);
      return overlayTypes[(idx + 1) % overlayTypes.length];
    });
  };

  // Add/remove overlay when overlayType changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    // Remove all overlays
    Object.values(overlayMapTypeIdMap).forEach((typeId) => {
      if (typeId) map.removeOverlayMapTypeId(typeId);
    });
    // Add new overlay nếu không phải NONE
    if (
      overlayType !== 'NONE' &&
      overlayMapTypeIdMap[overlayType as Exclude<OverlayType, 'NONE'>]
    ) {
      const typeId =
        overlayMapTypeIdMap[overlayType as Exclude<OverlayType, 'NONE'>];
      if (typeId !== undefined) {
        map.addOverlayMapTypeId(typeId);
      }
    }
  }, [overlayType]);

  useEffect(() => {
    const map = mapRef.current;
    if (map && typeof map.relayout === 'function') {
      // Use longer timeout to ensure DOM is fully updated
      setTimeout(() => {
        map.relayout();
      }, 300);
    }
  }, [isFullscreen]);

  // Additional effect to handle window resize and ensure proper rendering
  useEffect(() => {
    const handleResize = () => {
      const map = mapRef.current;
      if (map && typeof map.relayout === 'function') {
        setTimeout(() => {
          map.relayout();
        }, 100);
      }
    };

    if (isFullscreen) {
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }
  }, [isFullscreen]);

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
          zIndex: 1001,
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
              size={20}
              color="#2D2E30"
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
              size={20}
              color="#2D2E30"
            />
          </button>
        </Box>
        <button
          onClick={handleToggleFullscreen}
          style={{
            ...btnStyle,
          }}
          type="button"
          title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        >
          {isFullscreen ? (
            <BiExitFullscreen
              size={20}
              color="#2D2E30"
            />
          ) : (
            <BiFullscreen
              size={20}
              color="#2D2E30"
            />
          )}
        </button>
      </Box>
      {/* Toggle Overlay Map Type Button */}
      <Box
        style={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        <Box>
          <button
            style={{
              ...btnStyle,
            }}
            onClick={handleToggleOverlay}
            title={overlayType}
            type="button"
          >
            <IoLayersOutline
              size={20}
              color="#2D2E30"
            />
          </button>
        </Box>
        {useAddLocation && (
          <button
            onClick={handleToggleAddLocation}
            style={{
              ...btnStyle,
              borderColor: isAddLocation ? '#000' : '#eee',
            }}
            type="button"
            title={isAddLocation ? 'Exit add location' : 'Add location'}
          >
            {isAddLocation ? (
              <MdAddLocation
                size={20}
                color="#2D2E30"
              />
            ) : (
              <MdOutlineAddLocation
                size={20}
                color="#2D2E30"
              />
            )}
          </button>
        )}
      </Box>
      <Map
        key={`map-${isFullscreen ? 'fullscreen' : 'normal'}`}
        ref={mapRef}
        center={centerMap}
        level={zoomLevel}
        isPanto={true}
        onCreate={(map) => {
          mapRef.current = map;
          setMapReady(true);
        }}
        style={{
          width: '100%',
          height: '100%',
          borderRadius: 8,
          filter:
            theme === 'dark'
              ? 'invert(1.5) hue-rotate(180deg)'
              : 'invert(0) hue-rotate(0deg)',
        }}
        onClick={(_, mouseEvent) => {
          if (!isAddLocation) {
            return;
          }

          const latlng = mouseEvent.latLng;

          handleAddLocation?.({
            lat: latlng.getLat(),
            lng: latlng.getLng(),
          });
        }}
      >
        {/* Route Groups - operating markers with blue color */}
        {routeGroups.map((route, groupIndex) => {
          const basePath = route
            .filter((marker) => isValidCoordinate(marker.lat, marker.lng))
            .map((marker) => ({
              lat: validateCoordinate(marker.lat)!,
              lng: validateCoordinate(marker.lng)!,
            }));

          const path =
            groupIndex === 1 ? offsetPath(basePath, 0.0005) : basePath;

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
                    <MapMarker
                      key={`group-${groupIndex}-${index}`}
                      position={{ lat, lng }}
                      title={marker.name}
                      image={smallMarkerImage('#4169e1')} // blue
                    />
                  );
                })}
              {basePath.length >= 2 && (
                <Polyline
                  path={path}
                  strokeWeight={4}
                  strokeColor={groupIndex === 0 ? '#FF0000' : '#0CBA47'}
                  strokeOpacity={0.7}
                  strokeStyle="solid"
                />
              )}
            </Fragment>
          );
        })}

        {/* markerData - standby markers with red color */}
        {filteredMarkerData.map((marker, index) => {
          const isSameAsDrone =
            dronePosition &&
            marker.lat === dronePosition.lat &&
            marker.lng === dronePosition.lng;
          if (isSameAsDrone) return null;

          return (
            <MapMarker
              key={`marker-${index}`}
              position={{ lat: marker.lat, lng: marker.lng }}
              image={{
                src: RouteIcon,
                size: { width: 24, height: 35 },
                options: { offset: { x: 12, y: 35 } },
              }} // red
              title={marker.name}
              clickable={!!onMarkerClick}
              onClick={() => {
                if (onMarkerClick) {
                  onMarkerClick(marker);
                }
              }}
            />
          );
        })}

        {/* Polyline for markerData if more than 1 */}
        {filteredMarkerData.length > 1 && (
          <>
            {filteredMarkerData.map((marker, index) => {
              if (index === filteredMarkerData.length - 1) return null; // Skip last marker

              const nextMarker = filteredMarkerData[index + 1];
              const isRobotRoute = marker.for_robot; // only check the first point of the route

              return (
                <Polyline
                  key={`polyline-${index}`}
                  path={[
                    { lat: marker.lat, lng: marker.lng },
                    { lat: nextMarker.lat, lng: nextMarker.lng },
                  ]}
                  strokeWeight={4}
                  strokeColor={isRobotRoute ? '#22c55e' : '#0CBA47'}
                  strokeOpacity={0.7}
                  strokeStyle="solid"
                />
              );
            })}
          </>
        )}

        {/* Drone position marker (if any) */}
        {dronePosition && (
          <MapMarker
            position={dronePosition}
            image={{
              src: 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png',
              size: { width: 24, height: 35 },
              options: { offset: { x: 12, y: 35 } },
            }}
            title="Drone"
          />
        )}
      </Map>
    </div>
  );
};

export default React.memo(MapForRoute);
