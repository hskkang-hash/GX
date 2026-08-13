import { Box } from '@mui/material';
import {
  AdvancedMarker,
  Map as GoogleMap,
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
import {
  Polyline as KakaoPolyline,
  Map,
  MapMarker,
  useKakaoLoader,
} from 'react-kakao-maps-sdk';
import {
  CustomBtn,
  CustomModal,
  useConfigGroupSystem,
  useTheme,
} from 'rj-core';

import { Polyline as GooglePolyline } from '@/components/maps/PolylineGoogleMap';
import { MAP_CONFIG } from '@/configs/Constant';
import { MapControls } from '@/features/SurveyMission/components/drawing';
import {
  getGeographicCenterAndZoomGoogle,
  getGeographicCenterAndZoomKakao,
} from '@/features/routes/utils/calculateCenterAndZoom';

type Marker = {
  lat: number;
  lng: number;
  name?: string;
  color?: string;
  operating_altitude?: number;
  routeId?: string | number;
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

const overlayMapTypeIdMap: Record<
  Exclude<OverlayType, 'NONE'>,
  kakao.maps.MapTypeId | undefined
> = {
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
  ROADMAP:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId.ROADMAP
      : undefined,
  SKYVIEW:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId.SKYVIEW
      : undefined,
  HYBRID:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId.HYBRID
      : undefined,
  OVERLAY:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId.OVERLAY
      : undefined,
  BICYCLE:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId.BICYCLE
      : undefined,
  BICYCLE_HYBRID:
    typeof window !== 'undefined' && window.kakao
      ? window.kakao.maps.MapTypeId.BICYCLE_HYBRID
      : undefined,
};

interface DroneRoute {
  route_path: Array<{
    lat: number;
    lng: number;
    name?: string;
    altitude?: number;
  }>;
  device: {
    id?: number;
    name?: string;
    color?: string;
  } | null;
}

interface CoordinatePickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (coordinates: [number, number]) => void;
  initialCoordinates?: [number, number] | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  selectedDrone?: any | null;
  markerData?: Marker[];
  isLineMode?: boolean;
  droneRoutes?: DroneRoute[];
}

const DEFAULT_CENTER = { lat: 37.4322793, lng: 127.1295062 };

// Component to handle Google Maps auto-bounds
const GoogleMapBoundsHandler: React.FC<{
  markerData: Marker[];
  droneRoutes: DroneRoute[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  selectedDrone?: any;
  selectedCoordinates: { lat: number; lng: number } | null;
  isOpen: boolean;
}> = ({
  markerData,
  droneRoutes,
  selectedDrone,
  selectedCoordinates,
  isOpen,
}) => {
  const map = useMap();
  const [shouldFitBounds, setShouldFitBounds] = useState(false);
  const hasFittedRef = useRef(false);

  // Trigger bounds fitting when modal opens and map is ready
  useEffect(() => {
    if (isOpen && map) {
      console.log('Google Map - Modal opened, triggering bounds fit');
      hasFittedRef.current = false;
      setShouldFitBounds(true);
    } else if (!isOpen) {
      hasFittedRef.current = false;
    }
  }, [isOpen, map]);

  // Wait for map to be idle (fully loaded) before fitting bounds
  useEffect(() => {
    if (!map || !isOpen) return;

    const listener = map.addListener('idle', () => {
      if (!hasFittedRef.current) {
        console.log('Google Map - Map is idle, triggering bounds fit');
        setShouldFitBounds(true);
      }
    });

    return () => {
      if (listener) {
        google.maps.event.removeListener(listener);
      }
    };
  }, [map, isOpen]);

  useEffect(() => {
    if (!map || !isOpen || !shouldFitBounds || hasFittedRef.current) {
      console.log('Google Map - Skipping bounds:', {
        hasMap: !!map,
        isOpen,
        shouldFitBounds,
        hasFitted: hasFittedRef.current,
      });
      return;
    }

    console.log('Google Map - Starting bounds calculation');

    // Longer delay to ensure map is fully initialized and rendered
    const timer = setTimeout(() => {
      const bounds = new google.maps.LatLngBounds();
      let hasPoints = false;

      // Add marker points
      if (markerData && markerData.length > 0) {
        markerData.forEach((marker) => {
          bounds.extend({ lat: marker.lat, lng: marker.lng });
          hasPoints = true;
        });
        console.log('Google Map - Added marker points:', markerData.length);
      }

      // Add drone route points
      if (droneRoutes && droneRoutes.length > 0) {
        droneRoutes.forEach((route) => {
          if (route.route_path && route.route_path.length > 0) {
            route.route_path.forEach((point) => {
              bounds.extend({ lat: point.lat, lng: point.lng });
              hasPoints = true;
            });
          }
        });
        console.log('Google Map - Added route points');
      }

      // Add drone terminal position
      // if (
      //   selectedDrone?.device?.terminal_latitude &&
      //   selectedDrone?.device?.terminal_longitude
      // ) {
      //   const droneLat = Number(selectedDrone.device.terminal_latitude);
      //   const droneLng = Number(selectedDrone.device.terminal_longitude);

      //   console.log('Google Map - Drone coordinates:', {
      //     lat: droneLat,
      //     lng: droneLng,
      //     raw: {
      //       lat: selectedDrone.device.terminal_latitude,
      //       lng: selectedDrone.device.terminal_longitude,
      //     },
      //   });

      //   if (!isNaN(droneLat) && !isNaN(droneLng)) {
      //     bounds.extend({
      //       lat: droneLat,
      //       lng: droneLng,
      //     });
      //     hasPoints = true;
      //     console.log('Google Map - Drone position added to bounds');
      //   }
      // }

      // Add selected coordinates
      if (selectedCoordinates) {
        bounds.extend(selectedCoordinates);
        hasPoints = true;
        console.log('Google Map - Added selected coordinates');
      }

      // Fit bounds if we have points
      if (hasPoints) {
        console.log('Google Map - Fitting bounds with points');
        try {
          map.fitBounds(bounds, 50);
          console.log('Google Map - Bounds fitted successfully');
          hasFittedRef.current = true;
          setShouldFitBounds(false); // Reset flag after fitting
        } catch (error) {
          console.error('Google Map - Error fitting bounds:', error);
        }
      } else {
        console.log('Google Map - No points to fit bounds');
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [
    map,
    markerData,
    droneRoutes,
    selectedDrone,
    selectedCoordinates,
    isOpen,
    shouldFitBounds,
  ]);

  return null;
};

// Helper function to create pin icon SVG (similar to RoutePolylineKakao)
const createLocationPinIcon = (
  fillColor: string,
  scale: number = 1,
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

// Helper function to create colored drone icon SVG
const createDroneIcon = (fillColor: string, size: number = 32): string => {
  return btoa(`
   <svg width="${size}" height="${size}" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect width="48" height="48" fill="white" fill-opacity="0.01"/>
<path d="M11 11L19 19M37 37L29 29" stroke="${fillColor}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M37 11L29 19M11 37L19 29" stroke="${fillColor}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
<rect x="19" y="19" width="10" height="10" fill="${fillColor}" stroke="${fillColor}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M37 18C38.3845 18 39.7379 17.5895 40.889 16.8203C42.0401 16.0511 42.9373 14.9579 43.4672 13.6788C43.997 12.3997 44.1356 10.9922 43.8655 9.63437C43.5954 8.2765 42.9287 7.02922 41.9498 6.05026C40.9708 5.07129 39.7235 4.4046 38.3656 4.13451C37.0078 3.86441 35.6003 4.00303 34.3212 4.53285C33.0421 5.06266 31.9489 5.95987 31.1797 7.11101C30.4105 8.26215 30 9.61553 30 11M37 30C38.3845 30 39.7379 30.4105 40.889 31.1797C42.0401 31.9489 42.9373 33.0421 43.4672 34.3212C43.997 35.6003 44.1356 37.0078 43.8655 38.3656C43.5954 39.7235 42.9287 40.9708 41.9498 41.9497C40.9708 42.9287 39.7235 43.5954 38.3656 43.8655C37.0078 44.1356 35.6003 43.997 34.3212 43.4672C33.0421 42.9373 31.9489 42.0401 31.1797 40.889C30.4105 39.7379 30 38.3845 30 37M11 18C9.61553 18 8.26216 17.5895 7.11101 16.8203C5.95987 16.0511 5.06266 14.9579 4.53285 13.6788C4.00303 12.3997 3.86441 10.9922 4.13451 9.63437C4.4046 8.2765 5.07129 7.02922 6.05026 6.05026C7.02922 5.07129 8.2765 4.4046 9.63437 4.13451C10.9922 3.86441 12.3997 4.00303 13.6788 4.53285C14.9579 5.06266 16.0511 5.95987 16.8203 7.11101C17.5895 8.26215 18 9.61553 18 11M11 30C9.61553 30 8.26216 30.4105 7.11101 31.1797C5.95987 31.9489 5.06266 33.0421 4.53285 34.3212C4.00303 35.6003 3.86441 37.0078 4.13451 38.3656C4.4046 39.7235 5.07129 40.9708 6.05026 41.9497C7.02922 42.9287 8.2765 43.5954 9.63437 43.8655C10.9922 44.1356 12.3997 43.997 13.6788 43.4672C14.9579 42.9373 16.0511 42.0401 16.8203 40.889C17.5895 39.7379 18 38.3845 18 37" stroke="${fillColor}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
  `);
};

const CoordinatePickerModal: React.FC<CoordinatePickerModalProps> = ({
  isOpen,
  onClose,
  onSave,
  selectedDrone,
  initialCoordinates,
  markerData = [],
  droneRoutes = [],
}) => {
  console.log('selectedDrone', selectedDrone);
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { configGroupSystem } = useConfigGroupSystem();
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;
  const mapRef = useRef<kakao.maps.Map | null>(null);

  const [overlayType, setOverlayType] = useState<OverlayType>('NONE');
  const [isFullscreen, setIsFullscreen] = useState(false);

  const useGoogleMap = isSystemUseGoogleMap || isEmptyConfigGroupSystem;

  // Calculate initial center from markerData, droneRoutes, and selectedDrone
  const calculateInitialCenter = useCallback(() => {
    // Collect all points from markerData, droneRoutes, and selectedDrone
    const allPoints: Array<{ lat: number; lng: number }> = [];

    // Add markerData points
    if (markerData && markerData.length > 0) {
      allPoints.push(...markerData.map((m) => ({ lat: m.lat, lng: m.lng })));
    }

    // Add droneRoutes points
    if (droneRoutes && droneRoutes.length > 0) {
      droneRoutes.forEach((route) => {
        if (route.route_path && route.route_path.length > 0) {
          allPoints.push(
            ...route.route_path.map((p) => ({ lat: p.lat, lng: p.lng })),
          );
        }
      });
    }

    // Add drone terminal position
    // if (
    //   selectedDrone?.device?.terminal_latitude &&
    //   selectedDrone?.device?.terminal_longitude
    // ) {
    //   const droneLat = Number(selectedDrone.device.terminal_latitude);
    //   const droneLng = Number(selectedDrone.device.terminal_longitude);

    //   if (!isNaN(droneLat) && !isNaN(droneLng)) {
    //     allPoints.push({ lat: droneLat, lng: droneLng });
    //     console.log('calculateInitialCenter - Added drone position:', {
    //       lat: droneLat,
    //       lng: droneLng,
    //     });
    //   }
    // }

    // If we have points, calculate center
    if (allPoints.length > 0) {
      console.log('calculateInitialCenter - Total points:', allPoints.length);
      if (useGoogleMap) {
        const { center, zoom } = getGeographicCenterAndZoomGoogle({
          stops: allPoints,
          map: null,
        });
        return {
          center: center || DEFAULT_CENTER,
          zoom: zoom || 15,
        };
      } else {
        const { center, zoom } = getGeographicCenterAndZoomKakao({
          stops: allPoints,
          map: null,
        });
        console.log('center', center);
        console.log('zoom', zoom);
        return {
          center: center || DEFAULT_CENTER,
          zoom: 5,
        };
      }
    }

    if (initialCoordinates) {
      return {
        center: { lat: initialCoordinates[0], lng: initialCoordinates[1] },
        zoom: 15,
      };
    }

    return {
      center: DEFAULT_CENTER,
      zoom: 15,
    };
  }, [
    markerData,
    droneRoutes,
    // selectedDrone,
    initialCoordinates,
    useGoogleMap,
  ]);

  const initialCenterAndZoom = useMemo(
    () => calculateInitialCenter(),
    [calculateInitialCenter],
  );

  const [selectedCoordinates, setSelectedCoordinates] = useState<{
    lat: number;
    lng: number;
  } | null>(
    initialCoordinates
      ? { lat: initialCoordinates[0], lng: initialCoordinates[1] }
      : null,
  );

  // Separate map center state - only updates when inputs change, not on map click
  const [mapCenter, setMapCenter] = useState<{
    lat: number;
    lng: number;
  }>(initialCenterAndZoom.center);

  const [kakaoMapReady, setKakaoMapReady] = useState(false);

  const [latInput, setLatInput] = useState(
    initialCoordinates ? initialCoordinates[0].toFixed(7) : '',
  );
  const [lngInput, setLngInput] = useState(
    initialCoordinates ? initialCoordinates[1].toFixed(7) : '',
  );

  const [zoomLevel, setZoomLevel] = useState(initialCenterAndZoom.zoom);

  // Initialize kakao loader for Kakao Maps
  useKakaoLoader({
    appkey: MAP_CONFIG.KAKAO_MAPS_API_KEY,
  });

  useEffect(() => {
    if (isOpen) {
      const { center, zoom } = calculateInitialCenter();

      if (initialCoordinates) {
        const coords = {
          lat: initialCoordinates[0],
          lng: initialCoordinates[1],
        };
        setSelectedCoordinates(coords);
        setLatInput(initialCoordinates[0].toFixed(7));
        setLngInput(initialCoordinates[1].toFixed(7));
      } else {
        setSelectedCoordinates(null);
        setLatInput('');
        setLngInput('');
      }

      setMapCenter(center);
      setZoomLevel(zoom);
    }
  }, [isOpen, initialCoordinates, calculateInitialCenter]);

  const handleMapClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (target: any, mouseEvent?: any) => {
      let lat: number, lng: number;

      if (useGoogleMap) {
        // Google Maps event structure - target is the event object
        if (target?.detail?.latLng) {
          const latLng = target.detail.latLng;
          // Handle both function and property access
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
            return;
          }
        } else {
          return;
        }
      } else {
        // Kakao Maps event structure - mouseEvent is the second parameter
        if (mouseEvent?.latLng) {
          lat = mouseEvent.latLng.getLat();
          lng = mouseEvent.latLng.getLng();
        } else {
          return;
        }
      }

      setSelectedCoordinates({ lat, lng });
      setLatInput(lat.toFixed(7));
      setLngInput(lng.toFixed(7));
    },
    [useGoogleMap],
  );

  const handleLatInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLatInput(value);
    const numValue = parseFloat(value);
    if (!isNaN(numValue) && numValue >= -90 && numValue <= 90) {
      setSelectedCoordinates((prev) =>
        prev ? { ...prev, lat: numValue } : { lat: numValue, lng: 0 },
      );
      setMapCenter((prev) => ({ ...prev, lat: numValue }));
    }
  };

  const handleLngInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLngInput(value);
    const numValue = parseFloat(value);
    if (!isNaN(numValue) && numValue >= -180 && numValue <= 180) {
      setSelectedCoordinates((prev) =>
        prev ? { ...prev, lng: numValue } : { lat: 0, lng: numValue },
      );
      setMapCenter((prev) => ({ ...prev, lng: numValue }));
    }
  };

  const handleSave = () => {
    const lat = parseFloat(latInput);
    const lng = parseFloat(lngInput);
    if (!isNaN(lat) && !isNaN(lng)) {
      onSave([lat, lng]);
      onClose();
    }
  };

  const handleZoomIn = () => {
    if (useGoogleMap) {
      // Google Maps: higher zoom = more zoomed in
      setZoomLevel((prev) => Math.min(prev + 1, 21));
    } else {
      // Kakao Maps: lower level = more zoomed in
      setZoomLevel((prev) => Math.max(prev - 1, 1));
    }
  };

  const handleZoomOut = () => {
    if (useGoogleMap) {
      // Google Maps: lower zoom = more zoomed out
      setZoomLevel((prev) => Math.max(prev - 1, 1));
    } else {
      // Kakao Maps: higher level = more zoomed out
      setZoomLevel((prev) => Math.min(prev + 1, 14));
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 12px',
    borderRadius: '6px',
    border: `1px solid ${theme === 'dark' ? '#303030' : '#d9d9d9'}`,
    backgroundColor: theme === 'dark' ? '#1F1F20' : '#fff',
    color: theme === 'dark' ? '#ececef' : '#000',
    fontSize: '14px',
  };

  const labelStyle: React.CSSProperties = {
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '8px',
    color: theme === 'dark' ? '#ececef' : '#000',
  };

  const handleToggleFullscreen = () => setIsFullscreen((f) => !f);

  // Toggle overlay type
  const handleToggleOverlay = (): void => {
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

  // Reset kakaoMapReady when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      // Reset when modal opens to wait for new map instance
      setKakaoMapReady(false);
      console.log('Kakao Map - Modal opened, reset kakaoMapReady');
    }
  }, [isOpen]);

  // Auto-bound Kakao Map when data changes
  useEffect(() => {
    if (useGoogleMap || !mapRef.current || !isOpen || !kakaoMapReady) {
      console.log('Kakao Map - Skipping bounds:', {
        useGoogleMap,
        hasMap: !!mapRef.current,
        isOpen,
        kakaoMapReady,
      });
      return;
    }

    const map = mapRef.current;
    console.log('Kakao Map - Starting bounds calculation');

    // Longer delay to ensure map is fully initialized and rendered
    const timer = setTimeout(() => {
      const bounds = new kakao.maps.LatLngBounds();
      let hasPoints = false;

      // Add marker points
      if (markerData && markerData.length > 0) {
        markerData.forEach((marker) => {
          bounds.extend(new kakao.maps.LatLng(marker.lat, marker.lng));
          hasPoints = true;
        });
        console.log('Kakao Map - Added marker points:', markerData.length);
      }

      // Add drone route points
      if (droneRoutes && droneRoutes.length > 0) {
        droneRoutes.forEach((route) => {
          if (route.route_path && route.route_path.length > 0) {
            route.route_path.forEach((point) => {
              bounds.extend(new kakao.maps.LatLng(point.lat, point.lng));
              hasPoints = true;
            });
          }
        });
        console.log('Kakao Map - Added route points');
      }

      // Add drone terminal position
      // if (
      //   selectedDrone?.device?.terminal_latitude &&
      //   selectedDrone?.device?.terminal_longitude
      // ) {
      //   const droneLat = Number(selectedDrone.device.terminal_latitude);
      //   const droneLng = Number(selectedDrone.device.terminal_longitude);

      //   console.log('Kakao Map - Drone coordinates:', {
      //     lat: droneLat,
      //     lng: droneLng,
      //     raw: {
      //       lat: selectedDrone.device.terminal_latitude,
      //       lng: selectedDrone.device.terminal_longitude,
      //     },
      //   });

      //   if (!isNaN(droneLat) && !isNaN(droneLng)) {
      //     bounds.extend(new kakao.maps.LatLng(droneLat, droneLng));
      //     hasPoints = true;
      //     console.log('Kakao Map - Drone position added to bounds');
      //   }
      // }

      // Add selected coordinates
      if (selectedCoordinates) {
        bounds.extend(
          new kakao.maps.LatLng(
            selectedCoordinates.lat,
            selectedCoordinates.lng,
          ),
        );
        hasPoints = true;
        console.log('Kakao Map - Added selected coordinates');
      }

      // Fit bounds if we have points
      if (hasPoints) {
        console.log('Kakao Map - Fitting bounds with points');
        try {
          map.setBounds(bounds);
          console.log('Kakao Map - Bounds fitted successfully');
        } catch (error) {
          console.error('Kakao Map - Error fitting bounds:', error);
        }
      } else {
        console.log('Kakao Map - No points to fit bounds');
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [
    useGoogleMap,
    markerData,
    droneRoutes,
    // selectedDrone,
    selectedCoordinates,
    isOpen,
    kakaoMapReady,
  ]);

  return (
    <CustomModal
      title={t('Select Waiting Coordinates')}
      show={isOpen}
      onHide={onClose}
      size="lg"
    >
      <Box sx={{ width: '60vw', maxWidth: '900px' }}>
        <p
          style={{
            color: theme === 'dark' ? '#a8a8a8' : '#666',
            marginBottom: '16px',
          }}
        >
          {t('Please click on the map to select the waiting coordinate.')}
        </p>

        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '16px',
            marginBottom: '16px',
          }}
        >
          <div>
            <div style={labelStyle}>{t('Latitude')}</div>
            <input
              type="number"
              step="0.0000001"
              value={latInput}
              onChange={handleLatInputChange}
              placeholder="37.4322793"
              style={inputStyle}
            />
          </div>
          <div>
            <div style={labelStyle}>{t('Longitude')}</div>
            <input
              type="number"
              step="0.0000001"
              value={lngInput}
              onChange={handleLngInputChange}
              placeholder="127.1295062"
              style={inputStyle}
            />
          </div>
        </Box>

        <Box
          sx={{
            position: 'relative',
            width: '100%',
            height: '500px',
            borderRadius: '8px',
            overflow: 'hidden',
            marginBottom: '16px',
          }}
        >
          {useGoogleMap ? (
            <GoogleMap
              center={mapCenter}
              zoom={zoomLevel}
              mapId="coordinate-picker-map"
              style={{ width: '100%', height: '100%' }}
              onClick={handleMapClick}
              streetViewControl={false}
              fullscreenControl={false}
              mapTypeControl={false}
              zoomControl={false}
            >
              {/* Auto-bounds handler */}
              <GoogleMapBoundsHandler
                markerData={markerData}
                droneRoutes={droneRoutes}
                selectedDrone={selectedDrone}
                selectedCoordinates={selectedCoordinates}
                isOpen={isOpen}
              />

              {/* Render existing markers from markerData with colors */}
              {markerData.map((marker, idx) => {
                const markerColor = marker.color || '#2378d9';
                const iconSize = 40;
                const pinIcon = createLocationPinIcon(markerColor, 1);

                return (
                  <AdvancedMarker
                    key={`marker-${idx}`}
                    position={{ lat: marker.lat, lng: marker.lng }}
                  >
                    <img
                      src={`data:image/svg+xml;base64,${pinIcon}`}
                      alt={marker.name || 'Waypoint'}
                      style={{
                        width: `${iconSize}px`,
                        height: `${iconSize}px`,
                        transform: 'translate(-50%, -100%)',
                      }}
                    />
                  </AdvancedMarker>
                );
              })}

              {/* Render drone routes */}
              {droneRoutes.map((route, idx) => {
                if (!route.route_path || route.route_path.length === 0)
                  return null;
                const path = route.route_path.map((point) => ({
                  lat: point.lat,
                  lng: point.lng,
                }));
                return (
                  <GooglePolyline
                    key={`route-${idx}`}
                    path={path}
                    strokeColor={route.device?.color || '#1D9BE2'}
                    strokeWeight={3}
                    strokeOpacity={0.8}
                  />
                );
              })}

              {/* Render drone marker at terminal position */}
              {/* {selectedDrone?.device?.terminal_latitude &&
                selectedDrone?.device?.terminal_longitude && (
                  <AdvancedMarker
                    position={{
                      lat: selectedDrone.device.terminal_latitude,
                      lng: selectedDrone.device.terminal_longitude,
                    }}
                  >
                    <img
                      src={`data:image/svg+xml;base64,${createDroneIcon(
                        selectedDrone.device.color || '#1D9BE2',
                        32,
                      )}`}
                      alt="Drone"
                      style={{
                        width: '32px',
                        height: '32px',
                        transform: 'translate(-50%, -50%)',
                      }}
                    />
                  </AdvancedMarker>
                )} */}

              {/* Render selected coordinates marker (always on top) with distinct color */}
              {selectedCoordinates && (
                <AdvancedMarker position={selectedCoordinates}>
                  <img
                    src={`data:image/svg+xml;base64,${createLocationPinIcon(
                      '#FF6B00',
                      1.2,
                    )}`}
                    alt={t('Waiting Coordinates')}
                    style={{
                      width: '48px',
                      height: '48px',
                      transform: 'translate(-50%, -100%)',
                    }}
                  />
                </AdvancedMarker>
              )}
            </GoogleMap>
          ) : (
            <div
              style={{
                width: '100%',
                position: isFullscreen ? 'fixed' : 'relative',
                top: isFullscreen ? 0 : undefined,
                left: isFullscreen ? 0 : undefined,
                zIndex: isFullscreen ? 9999 : undefined,
                borderRadius: 8,
                height: isFullscreen ? '100vh' : '500px',
              }}
            >
              {/* Map Controls */}
              <MapControls
                isFullscreen={isFullscreen}
                onToggleFullscreen={handleToggleFullscreen}
                onZoomIn={handleZoomIn}
                onZoomOut={handleZoomOut}
                onToggleOverlay={handleToggleOverlay}
                overlayType={overlayType}
                theme={theme}
              />
              <Map
                ref={mapRef}
                center={mapCenter}
                level={zoomLevel}
                onClick={handleMapClick}
                onCreate={(map) => {
                  console.log('Kakao Map - onCreate called');
                  mapRef.current = map;
                  setKakaoMapReady(true);
                }}
                style={{
                  width: '100%',
                  height: '100%',
                  borderRadius: 8,
                  // Apply filter only to map tiles, not to children elements
                  filter:
                    theme === 'dark'
                      ? 'invert(1.5) hue-rotate(180deg)'
                      : 'invert(0) hue-rotate(0deg)',
                }}
              >
                {/* Render existing markers from markerData with colors */}
                {/* {markerData.map((marker, idx) => {
                  const markerColor = marker.color || '#2378d9';
                  const iconSize = 40;
                  const scale = 1;

                  return (
                    <MapMarker
                      key={`marker-${idx}`}
                      position={{ lat: marker.lat, lng: marker.lng }}
                      image={{
                        src: `data:image/svg+xml;base64,${createLocationPinIcon(markerColor, scale)}`,
                        size: { width: iconSize, height: iconSize },
                        options: { offset: { x: iconSize / 2, y: iconSize } },
                      }}
                      title={marker.name || `Waypoint ${idx + 1}`}
                      zIndex={3}
                    />
                  );
                })} */}

                {/* Render drone routes */}
                {droneRoutes.map((route, idx) => {
                  if (!route.route_path || route.route_path.length === 0)
                    return null;
                  const path = route.route_path.map((point) => ({
                    lat: point.lat,
                    lng: point.lng,
                  }));
                  return (
                    <KakaoPolyline
                      key={`route-${idx}`}
                      path={path}
                      strokeColor={route.device?.color || '#1D9BE2'}
                      strokeWeight={3}
                      strokeOpacity={0.8}
                    />
                  );
                })}

                {/* Render drone marker at terminal position */}
                {/* {selectedDrone?.device?.terminal_latitude &&
                  selectedDrone?.device?.terminal_longitude && (
                    <MapMarker
                      position={{
                        lat: selectedDrone.device.terminal_latitude,
                        lng: selectedDrone.device.terminal_longitude,
                      }}
                      image={{
                        src: `data:image/svg+xml;base64,${createDroneIcon(selectedDrone.device.color || '#1D9BE2', 32)}`,
                        size: { width: 32, height: 32 },
                        options: { offset: { x: 16, y: 16 } },
                      }}
                      title={`Drone: ${selectedDrone.device.name}`}
                      zIndex={50}
                    />
                  )} */}

                {/* Render selected coordinates marker (always on top) with distinct color */}
                {selectedCoordinates && (
                  <MapMarker
                    position={selectedCoordinates}
                    image={{
                      src: `data:image/svg+xml;base64,${createLocationPinIcon('#FF6B00', 1.2)}`,
                      size: { width: 48, height: 48 },
                      options: { offset: { x: 24, y: 48 } },
                    }}
                    title={t('Waiting Coordinates')}
                    zIndex={100}
                  />
                )}
              </Map>
            </div>
          )}
        </Box>

        <Box
          sx={{
            width: '100%',
            display: 'flex',
            gap: '12px',
            justifyContent: 'center',
            marginBottom: '1rem',
          }}
        >
          <CustomBtn
            label={t('Save')}
            color="primary"
            size="lg"
            onClick={handleSave}
          />
          <CustomBtn
            label={t('Close')}
            variant="outline"
            color="secondary"
            size="lg"
            onClick={onClose}
          />
        </Box>
      </Box>
    </CustomModal>
  );
};

export default CoordinatePickerModal;
