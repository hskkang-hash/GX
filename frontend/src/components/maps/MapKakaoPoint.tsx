import { Box } from '@mui/material';
import React, { useRef, useState, useEffect, useMemo } from 'react';
import { BiFullscreen, BiExitFullscreen } from 'react-icons/bi';
import { FiPlus, FiMinus } from 'react-icons/fi';
import { IoLayersOutline } from 'react-icons/io5';
import {
  Map,
  MapMarker,
  Polyline,
  CustomOverlayMap,
} from 'react-kakao-maps-sdk';
import { useTheme } from 'rj-core';

export interface MarkerData {
  lat: number;
  lng: number;
  name?: string;
  icon?: string;
  terminal_name?: string;
}

export interface PolylineOptions {
  path: Array<{ lat: number; lng: number }>;
  strokeColor?: string;
  strokeOpacity?: number;
  strokeStyle?: 'solid' | 'shortdash' | 'shortdot';
  strokeWeight?: number;
  type?: 'DRONE' | 'ROBOT';
}

export interface MapBounds {
  sw: { lat: number; lng: number };
  ne: { lat: number; lng: number };
}

interface MapKakaoProps {
  center?: { lat: number; lng: number };
  level?: number;
  operatingMarkers?: MarkerData[];
  standbyMarkers?: MarkerData[];
  polylines?: PolylineOptions[];
  style?: React.CSSProperties;
  overlayContent?: React.ReactNode;
  smallMarker?: boolean;
  bounds?: MapBounds;
  terminalAddress?: {
    droneStartAddress: { lat: number; lng: number; name: string };
    robotStartAddress: { lat: number; lng: number; name: string };
    droneEndAddress: { lat: number; lng: number; name: string };
    robotEndAddress: { lat: number; lng: number; name: string };
  }; // Điểm terminal ở giữa
}

const baseMapTypes = ['ROADMAP', 'SKYVIEW'] as const;
const overlayTypes = [
  'NONE',
  'TRAFFIC',
  'ROADVIEW',
  'TERRAIN',
  'USE_DISTRICT',
] as const;
type BaseMapType = (typeof baseMapTypes)[number];
type OverlayType = (typeof overlayTypes)[number];

const overlayMapTypeIdMap: Record<Exclude<OverlayType, 'NONE'>, any> = {
  TRAFFIC:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId.TRAFFIC
      : undefined,
  ROADVIEW:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId.ROADVIEW
      : undefined,
  TERRAIN:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId.TERRAIN
      : undefined,
  USE_DISTRICT:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId.USE_DISTRICT
      : undefined,
};

// Helper function to check if two positions are equal (within a small threshold)
const arePositionsEqual = (
  pos1: { lat: number; lng: number },
  pos2: { lat: number; lng: number },
  threshold = 0.0001,
) => {
  return (
    Math.abs(pos1.lat - pos2.lat) < threshold &&
    Math.abs(pos1.lng - pos2.lng) < threshold
  );
};

// Helper function to find terminal point and overall start/end points
const findRouteDetails = (polylines: PolylineOptions[]) => {
  const dronePath = polylines.find((p) => p.type === 'DRONE');
  const robotPath = polylines.find((p) => p.type === 'ROBOT');

  if (
    dronePath &&
    robotPath &&
    dronePath.path.length > 0 &&
    robotPath.path.length > 0
  ) {
    const droneStart = dronePath.path[0];
    const droneEnd = dronePath.path[dronePath.path.length - 1];
    const robotStart = robotPath.path[0];
    const robotEnd = robotPath.path[robotPath.path.length - 1];

    // Scenario 1: Drone -> Robot
    if (arePositionsEqual(droneEnd, robotStart)) {
      return {
        terminalPoint: droneEnd,
        startPoint: droneStart,
        endPoint: robotEnd,
      };
    }

    // Scenario 2: Robot -> Drone
    if (arePositionsEqual(robotEnd, droneStart)) {
      return {
        terminalPoint: robotEnd,
        startPoint: robotStart,
        endPoint: droneEnd,
      };
    }
  }

  // No connection found or invalid paths
  return {
    terminalPoint: null,
    startPoint: null,
    endPoint: null,
  };
};

const MapKakaoPoint: React.FC<MapKakaoProps> = ({
  center,
  level = 5,
  operatingMarkers = [],
  standbyMarkers = [],
  polylines = [],
  style = {},
  overlayContent,
  smallMarker = false,
  bounds,
  terminalAddress,
}) => {
  console.log({ operatingMarkers });
  const [theme] = useTheme();
  const [overlayType, setOverlayType] = useState<OverlayType>('NONE');
  const [zoomLevel, setZoomLevel] = useState(level);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const mapRef = useRef<any>(null);

  // use memo to calculate route details stable
  const routeDetails = useMemo(() => {
    return findRouteDetails(polylines);
  }, [polylines]);

  // use memo to calculate finalTerminalPoint stable
  const finalTerminalPoint = useMemo(() => {
    const { terminalPoint: autoTerminalPoint } = routeDetails;

    if (!autoTerminalPoint) return null;

    // check if autoTerminalPoint is equal to terminalAddress
    if (
      terminalAddress?.droneEndAddress &&
      arePositionsEqual(autoTerminalPoint, terminalAddress.droneEndAddress)
    ) {
      return terminalAddress.droneEndAddress;
    }

    if (
      terminalAddress?.robotStartAddress &&
      arePositionsEqual(autoTerminalPoint, terminalAddress.robotStartAddress)
    ) {
      return terminalAddress.robotStartAddress;
    }

    // if not equal to terminalAddress, use autoTerminalPoint with default name
    return {
      ...autoTerminalPoint,
      name: 'Terminal',
    };
  }, [routeDetails, terminalAddress]);

  // toggle overlay type
  const handleToggleOverlay = () => {
    setOverlayType((prev) => {
      const idx = overlayTypes.indexOf(prev);
      return overlayTypes[(idx + 1) % overlayTypes.length];
    });
  };

  // zoom controls
  const handleZoomIn = () => {
    if (mapRef.current) {
      const newLevel = Math.max(1, zoomLevel - 1);
      mapRef.current.setLevel(newLevel);
      setZoomLevel(newLevel);
    }
  };
  const handleZoomOut = () => {
    if (mapRef.current) {
      const newLevel = Math.min(14, zoomLevel + 1);
      mapRef.current.setLevel(newLevel);
      setZoomLevel(newLevel);
    }
  };
  const handleToggleFullscreen = () => setIsFullscreen((f) => !f);

  // add/remove overlay when overlayType changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    // Remove all overlays
    Object.values(overlayMapTypeIdMap).forEach((typeId) => {
      if (typeId) map.removeOverlayMapTypeId(typeId);
    });
    // add new overlay if not NONE
    if (
      overlayType !== 'NONE' &&
      overlayMapTypeIdMap[overlayType as Exclude<OverlayType, 'NONE'>]
    ) {
      map.addOverlayMapTypeId(
        overlayMapTypeIdMap[overlayType as Exclude<OverlayType, 'NONE'>],
      );
    }
  }, [overlayType]);

  // onCreate callback to set bounds
  const handleMapCreate = React.useCallback(
    (map: kakao.maps.Map) => {
      if (bounds && window.kakao && window.kakao.maps) {
        const kakaoBounds = new window.kakao.maps.LatLngBounds(
          new window.kakao.maps.LatLng(bounds.sw.lat, bounds.sw.lng),
          new window.kakao.maps.LatLng(bounds.ne.lat, bounds.ne.lng),
        );
        map.setBounds(kakaoBounds);
      }
    },
    [bounds],
  );

  useEffect(() => {
    const map = mapRef.current;
    if (map && typeof map.relayout === 'function') {
      setTimeout(() => {
        map.relayout();
      }, 100);
    }
  }, [isFullscreen]);

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

  const {
    terminalPoint: autoTerminalPoint,
    startPoint,
    endPoint,
  } = routeDetails;

  console.log(finalTerminalPoint, 'finalTerminalPoint');
  console.log({ finalTerminalPoint });

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
        title={overlayType}
      >
        <IoLayersOutline
          size={24}
          color={theme === 'dark' ? '#ececef' : '#2D2E30'}
        />
      </div>
      <Map
        key={`map-${isFullscreen ? 'fullscreen' : 'normal'}-${theme}`}
        ref={mapRef}
        center={
          center || {
            lat: autoTerminalPoint?.lat || 36.5184,
            lng: autoTerminalPoint?.lng || 126.8,
          }
        }
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
        draggable={true}
        zoomable={true} // Bật scroll zoom
      >
        {/* Polyline paths */}
        {polylines.map((path, idx) => (
          <React.Fragment key={'polyfrag-' + idx}>
            <Polyline
              key={'poly-' + idx}
              path={path.path}
              strokeWeight={path.strokeWeight || 4}
              strokeColor={path.strokeColor || '#e74c3c'}
              strokeOpacity={path.strokeOpacity || 0.7}
              strokeStyle={path.strokeStyle || 'solid'}
            />
          </React.Fragment>
        ))}

        {/* Start marker */}
        {startPoint && (
          <MapMarker
            position={startPoint}
            image={{
              src: "data:image/svg+xml;utf8,<svg width='40' height='40' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z' fill='%2303c768'/><text x='12' y='11' font-size='6' text-anchor='middle' fill='white' font-family='Arial' font-weight='bold'>출발</text></svg>",
              size: { width: 40, height: 40 },
              options: { offset: { x: 20, y: 37 } },
            }}
            title="Start Point"
          />
        )}

        {/* End marker */}
        {endPoint && (
          <MapMarker
            position={endPoint}
            image={{
              src: "data:image/svg+xml;utf8,<svg width='40' height='40' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path d='M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z' fill='%23e8445e'/><text x='12' y='11' font-size='6' text-anchor='middle' fill='white' font-family='Arial' font-weight='bold'>도착</text></svg>",
              size: { width: 40, height: 40 },
              options: { offset: { x: 20, y: 37 } },
            }}
            title="End Point"
          />
        )}

        {/* Terminal marker */}
        {finalTerminalPoint && (
          <CustomOverlayMap
            position={finalTerminalPoint}
            yAnchor={1.5}
          >
            <div
              style={{
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                filter: 'drop-shadow(0 2px 3px rgba(0,0,0,0.2))',
              }}
            >
              <div
                style={{
                  background: 'white',
                  borderRadius: '16px',
                  padding: '4px 10px 4px 4px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  border: '1px solid #B0B0B0',
                }}
              >
                <div
                  style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    backgroundColor: '#6DD400',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                  }}
                >
                  <svg
                    fill="white"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path d="M4 16c0 .88.39 1.67 1 2.22V21h3v-2h8v2h3v-2.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5s-.67 1.5-1.5 1.5zM18 11H6V6h12v5z" />
                  </svg>
                </div>
                <span
                  style={{
                    fontWeight: 'bold',
                    fontSize: '14px',
                    color: '#333',
                  }}
                >
                  {finalTerminalPoint.name || 'Terminal'}
                </span>
              </div>
              <div
                style={{
                  // The pin "leg"
                  width: '1px',
                  height: '12px',
                  backgroundColor: 'black',
                  position: 'absolute',
                  bottom: '-12px',
                  left: '50%', // Adjust to be under the circle icon
                  transform: 'translateX(-50%)',
                }}
              ></div>
              <div
                style={{
                  // The pin circle
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: 'white',
                  border: '1px solid black',
                  position: 'absolute',
                  bottom: '-16px',
                  left: '50%', // Adjust to be under the circle icon
                  transform: 'translateX(-50%)',
                }}
              ></div>
            </div>
          </CustomOverlayMap>
        )}

        {/* Operating markers */}
        {operatingMarkers
          .filter((marker) => {
            // Don't show operating markers if they are the start, end, or terminal points
            if (!startPoint || !endPoint || !autoTerminalPoint) return true;
            return (
              !arePositionsEqual(marker, startPoint) &&
              !arePositionsEqual(marker, endPoint) &&
              !arePositionsEqual(marker, autoTerminalPoint)
            );
          })
          .map((marker, idx) => {
            return marker?.icon ? (
              <MapMarker
                key={'op-' + idx}
                position={{ lat: marker.lat, lng: marker.lng }}
                image={{
                  src: marker.icon,
                  size: { width: 40, height: 40 },
                  options: { offset: { x: 8, y: 8 } },
                }}
                title={marker?.name || marker?.terminal_name}
              />
            ) : smallMarker ? (
              <MapMarker
                key={'op-' + idx}
                position={{ lat: marker.lat, lng: marker.lng }}
                image={{
                  src: "data:image/svg+xml;utf8,<svg width='16' height='16' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23fd0000'><path d='M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z'/></svg>",
                  size: { width: 16, height: 16 },
                  options: { offset: { x: 8, y: 8 } },
                }}
                title={marker.name || marker.terminal_name}
              />
            ) : (
              <MapMarker
                key={'op-' + idx}
                position={{ lat: marker.lat, lng: marker.lng }}
                image={{
                  src: "data:image/svg+xml;utf8,<svg width='32' height='32' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23fd0000' opacity='0.85'><path d='M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z'/></svg>",
                  size: { width: 32, height: 32 },
                  options: { offset: { x: 16, y: 28 } },
                }}
                title={marker.name || marker.terminal_name}
              />
            );
          })}
        {/* Standby markers */}
        {standbyMarkers
          .filter((marker) => {
            // Don't show standby markers if they are the start, end, or terminal points
            if (!startPoint || !endPoint || !autoTerminalPoint) return true;
            return (
              !arePositionsEqual(marker, startPoint) &&
              !arePositionsEqual(marker, endPoint) &&
              !arePositionsEqual(marker, autoTerminalPoint)
            );
          })
          .map((marker, idx) =>
            smallMarker ? (
              <MapMarker
                key={'st-' + idx}
                position={{ lat: marker.lat, lng: marker.lng }}
                image={{
                  src: "data:image/svg+xml;utf8,<svg width='16' height='16' xmlns='http://www.w3.org/2000/svg'><circle cx='8' cy='8' r='7' fill='%23e74c3c' stroke='white' stroke-width='2'/></svg>",
                  size: { width: 16, height: 16 },
                  options: { offset: { x: 8, y: 8 } },
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
                  options: { offset: { x: 12, y: 35 } },
                }}
                title={marker.name || marker.terminal_name}
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

export default MapKakaoPoint;
