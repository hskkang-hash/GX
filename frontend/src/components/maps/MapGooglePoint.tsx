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
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';
import styled from 'styled-components';

const GoogleMapWrapper = styled.div`
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
`;

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

interface MapGooglePointProps {
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
  };
  apiKey: string;
}

const mapTypes = ['roadmap', 'satellite', 'hybrid', 'terrain'] as const;
type MapType = (typeof mapTypes)[number];

// Helper function to convert Kakao Map level to Google Maps zoom
// Kakao level: 1 (most zoomed in) to 14 (most zoomed out)
// Google zoom: 1 (most zoomed out) to 20 (most zoomed in)
const convertKakaoLevelToGoogleZoom = (kakaoLevel: number): number => {
  // Invert the scale and map to appropriate Google zoom levels
  // Kakao level 1 -> Google zoom ~18
  // Kakao level 14 -> Google zoom ~3
  return Math.max(3, Math.min(18, 19 - kakaoLevel));
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

// Polyline component for Google Maps
const GooglePolyline = ({
  path,
  options,
}: {
  path: PolylineOptions['path'];
  options: Omit<PolylineOptions, 'path'>;
}) => {
  const map = useMap();
  const polylineRef = useRef<google.maps.Polyline | null>(null);

  useEffect(() => {
    if (!map || !path.length) return;

    // Clean up existing polyline
    const currentPolyline = polylineRef.current;
    if (currentPolyline) {
      currentPolyline.setMap(null);
    }

    // Create polyline
    const polyline = new google.maps.Polyline({
      path: path.map((point) => ({ lat: point.lat, lng: point.lng })),
      geodesic: true,
      strokeColor: options.strokeColor || '#e74c3c',
      strokeOpacity: options.strokeOpacity || 0.7,
      strokeWeight: options.strokeWeight || 4,
    });

    polyline.setMap(map);
    polylineRef.current = polyline;

    return () => {
      if (currentPolyline) {
        currentPolyline.setMap(null);
      }
    };
  }, [map, path, options]);

  return null;
};

// Custom overlay component for terminal marker
const TerminalOverlay = ({
  position,
  name,
}: {
  position: { lat: number; lng: number };
  name: string;
}) => {
  return (
    <AdvancedMarker position={position}>
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
            {name || 'Terminal'}
          </span>
        </div>
        <div
          style={{
            width: '1px',
            height: '12px',
            backgroundColor: 'black',
            position: 'absolute',
            bottom: '-12px',
            left: '50%',
            transform: 'translateX(-50%)',
          }}
        ></div>
        <div
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: 'white',
            border: '1px solid black',
            position: 'absolute',
            bottom: '-16px',
            left: '50%',
            transform: 'translateX(-50%)',
          }}
        ></div>
      </div>
    </AdvancedMarker>
  );
};

const MapGooglePointContent = ({
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
}: Omit<MapGooglePointProps, 'apiKey'>) => {
  const [theme] = useTheme();
  const [mapType, setMapType] = useState<MapType>('roadmap');
  const [zoom, setZoom] = useState<number>(
    convertKakaoLevelToGoogleZoom(level),
  );
  const [mapCenter, setMapCenter] = useState<{ lat: number; lng: number }>({
    lat: 36.5184,
    lng: 126.8,
  });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [hasInitializedBounds, setHasInitializedBounds] = useState(false);
  const map = useMap();

  // Calculate route details
  const routeDetails = useMemo(() => {
    return findRouteDetails(polylines);
  }, [polylines]);

  // Calculate final terminal point
  const finalTerminalPoint = useMemo(() => {
    const { terminalPoint: autoTerminalPoint } = routeDetails;

    if (!autoTerminalPoint) return null;

    // Check if autoTerminalPoint matches terminalAddress
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

    // If not equal to terminalAddress, use autoTerminalPoint with default name
    return {
      ...autoTerminalPoint,
      name: 'Terminal',
    };
  }, [routeDetails, terminalAddress]);

  const {
    terminalPoint: autoTerminalPoint,
    startPoint,
    endPoint,
  } = routeDetails;

  // Set initial center
  useEffect(() => {
    if (center) {
      setMapCenter(center);
    } else if (autoTerminalPoint) {
      setMapCenter(autoTerminalPoint);
    }
  }, [center, autoTerminalPoint]);

  // Calculate bounds from polylines and markers to fit all content
  useEffect(() => {
    if (
      map &&
      !hasInitializedBounds &&
      (polylines.length > 0 ||
        operatingMarkers.length > 0 ||
        standbyMarkers.length > 0 ||
        startPoint ||
        endPoint ||
        finalTerminalPoint)
    ) {
      const googleBounds = new google.maps.LatLngBounds();
      let hasPoints = false;

      // Add polyline points to bounds
      polylines.forEach((polyline) => {
        polyline.path.forEach((point) => {
          if (point.lat && point.lng) {
            googleBounds.extend(new google.maps.LatLng(point.lat, point.lng));
            hasPoints = true;
          }
        });
      });

      // Add marker points to bounds
      [...operatingMarkers, ...standbyMarkers].forEach((marker) => {
        if (marker.lat && marker.lng) {
          googleBounds.extend(new google.maps.LatLng(marker.lat, marker.lng));
          hasPoints = true;
        }
      });

      // Add start, end, and terminal points to bounds
      if (startPoint) {
        googleBounds.extend(
          new google.maps.LatLng(startPoint.lat, startPoint.lng),
        );
        hasPoints = true;
      }
      if (endPoint) {
        googleBounds.extend(new google.maps.LatLng(endPoint.lat, endPoint.lng));
        hasPoints = true;
      }
      if (finalTerminalPoint) {
        googleBounds.extend(
          new google.maps.LatLng(
            finalTerminalPoint.lat,
            finalTerminalPoint.lng,
          ),
        );
        hasPoints = true;
      }

      // Fit bounds if we have points
      if (hasPoints) {
        map.fitBounds(googleBounds, {
          top: 40,
          right: 40,
          bottom: 40,
          left: 40,
        });

        // Get the calculated zoom after fitBounds
        setTimeout(() => {
          const calculatedZoom = map.getZoom() || 13;
          setZoom(calculatedZoom);
          const calculatedCenter = map.getCenter();
          if (calculatedCenter) {
            setMapCenter({
              lat: calculatedCenter.lat(),
              lng: calculatedCenter.lng(),
            });
          }
          setHasInitializedBounds(true);
        }, 100);
      }
    }
  }, [
    map,
    polylines,
    operatingMarkers,
    standbyMarkers,
    startPoint,
    endPoint,
    finalTerminalPoint,
    hasInitializedBounds,
  ]);

  // Handle manual bounds if provided
  useEffect(() => {
    if (map && bounds) {
      const googleBounds = new google.maps.LatLngBounds(
        new google.maps.LatLng(bounds.sw.lat, bounds.sw.lng),
        new google.maps.LatLng(bounds.ne.lat, bounds.ne.lng),
      );
      map.fitBounds(googleBounds);
    }
  }, [map, bounds]);

  const handleCameraChange = useCallback((ev: MapCameraChangedEvent) => {
    setMapCenter(ev.detail.center);
    setZoom(ev.detail.zoom);
  }, []);

  const handleToggleMapType = () => {
    setMapType((prev) => {
      const idx = mapTypes.indexOf(prev);
      return mapTypes[(idx + 1) % mapTypes.length];
    });
  };

  const handleZoomIn = () => {
    if (map) {
      const currentZoom = map.getZoom() || zoom;
      const newZoom = Math.min(20, currentZoom + 1);
      map.setZoom(newZoom);
      setZoom(newZoom);
    }
  };

  const handleZoomOut = () => {
    if (map) {
      const currentZoom = map.getZoom() || zoom;
      const newZoom = Math.max(1, currentZoom - 1);
      map.setZoom(newZoom);
      setZoom(newZoom);
    }
  };

  const handleToggleFullscreen = () => {
    setIsFullscreen((f) => !f);
    setHasInitializedBounds(false); // Reset bounds to recalculate after fullscreen change
    // Trigger map resize after fullscreen toggle
    setTimeout(() => {
      if (map) {
        google.maps.event.trigger(map, 'resize');
      }
    }, 100);
  };

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
      <Map
        center={mapCenter}
        zoom={zoom}
        mapTypeId={mapType}
        mapId="guardianx-point-map"
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
        {/* Polylines */}
        {polylines.map((polyline, idx) => (
          <GooglePolyline
            key={`poly-${idx}`}
            path={polyline.path}
            options={polyline}
          />
        ))}

        {/* Start marker */}
        {startPoint && (
          <AdvancedMarker
            position={startPoint}
            title="Start Point"
          >
            <Pin
              background="#03c768"
              glyphColor="#ffffff"
              borderColor="#ffffff"
              scale={1.2}
            >
              <div
                style={{
                  fontSize: '10px',
                  fontWeight: 'bold',
                  color: 'white',
                  textAlign: 'center',
                }}
              >
                출발
              </div>
            </Pin>
          </AdvancedMarker>
        )}

        {/* End marker */}
        {endPoint && (
          <AdvancedMarker
            position={endPoint}
            title="End Point"
          >
            <Pin
              background="#e8445e"
              glyphColor="#ffffff"
              borderColor="#ffffff"
              scale={1.2}
            >
              <div
                style={{
                  fontSize: '10px',
                  fontWeight: 'bold',
                  color: 'white',
                  textAlign: 'center',
                }}
              >
                도착
              </div>
            </Pin>
          </AdvancedMarker>
        )}

        {/* Terminal marker */}
        {finalTerminalPoint && (
          <TerminalOverlay
            position={finalTerminalPoint}
            name={finalTerminalPoint.name || 'Terminal'}
          />
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
              <AdvancedMarker
                key={`op-${idx}`}
                position={{ lat: marker.lat, lng: marker.lng }}
                title={marker?.name || marker?.terminal_name}
              >
                <img
                  src={marker.icon}
                  alt={marker?.name || marker?.terminal_name}
                  style={{ width: 40, height: 40 }}
                />
              </AdvancedMarker>
            ) : (
              <AdvancedMarker
                key={`op-${idx}`}
                position={{ lat: marker.lat, lng: marker.lng }}
                title={marker.name || marker.terminal_name}
              >
                <Pin
                  background="#fd0000"
                  glyphColor="#ffffff"
                  borderColor="#ffffff"
                  scale={smallMarker ? 0.8 : 1.2}
                />
              </AdvancedMarker>
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
          .map((marker, idx) => (
            <AdvancedMarker
              key={`st-${idx}`}
              position={{ lat: marker.lat, lng: marker.lng }}
              title={marker.name || marker.terminal_name}
            >
              <Pin
                background="#e74c3c"
                glyphColor="#ffffff"
                borderColor="#ffffff"
                scale={smallMarker ? 0.6 : 1.0}
              />
            </AdvancedMarker>
          ))}
      </Map>

      {overlayContent && (
        <div
          style={{
            position: 'absolute',
            top: 52,
            right: 8,
            background:
              theme === 'dark'
                ? 'none 6px center / 28px no-repeat rgb(68, 68, 68)'
                : 'rgba(255,255,255,0.9)',
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

const MapGooglePoint = (props: MapGooglePointProps) => {
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
      <MapGooglePointContent {...props} />
    </APIProvider>
  );
};

export default React.memo(MapGooglePoint);
