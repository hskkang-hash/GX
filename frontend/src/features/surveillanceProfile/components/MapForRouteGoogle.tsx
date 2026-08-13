import {
  APIProvider,
  ColorScheme,
  ControlPosition,
  Map,
  MapCameraChangedEvent,
  MapMouseEvent,
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
import { useProfile, useTheme } from 'rj-core';
import styled from 'styled-components';

import { getGeographicCenterAndZoomGoogle } from '@/features/routes/utils/calculateCenterAndZoom';
import { useDrawingModeStore } from '@/features/surveillanceProfile/stores/drawingModeStore';

import RoutePolyline from './RoutePolyline';
import { useMapClickHandler } from './drawing/useMapClickHandler';
import {
  DrawingPoint,
  DrawingRenderer,
  DrawingToolbar,
  Marker,
  useDrawing,
} from './drawingGoogle';

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

interface DroneRoute {
  route_path?: Array<{
    latitude: number;
    longitude: number;
    name?: string;
  }>;
  device?: {
    id: number;
    name: string;
  };
}

type Props = {
  markerData?: Marker[];
  style?: React.CSSProperties;
  overlayContent?: React.ReactNode;
  getMapRef?: (map: google.maps.Map) => void;
  apiKey: string;
  isLineMode?: boolean;
  notUseActionButtons?: boolean;
  onMarkerClick?: (marker: Marker) => void;
  droneRoutes?: DroneRoute[];
};

const MapForRouteGoogleContent = ({
  markerData = [],
  style = {},
  getMapRef,
  overlayContent,
  isLineMode = false,
  notUseActionButtons = false,
  onMarkerClick,
  droneRoutes = [],
}: Omit<Props, 'apiKey'>) => {
  const [theme] = useTheme();
  const map = useMap();
  const isUpdatingRef = useRef(false);
  const prevMarkerDataRef = useRef<Marker[]>([]);
  const { profile } = useProfile();

  const mapCenterByCountry = useMemo(() => {
    const isGoogleMap =
      profile?.group__settings?.use_map?.select_map?.google_map;
    const countryCode = profile?.group__settings?.use_map?.country_code;

    if (!isGoogleMap) {
      return { center: { lat: 36.5184, lng: 126.8 }, zoom: 5 };
    }

    switch (countryCode) {
      case 'KR':
        return {
          center: { lat: 37.5665, lng: 126.978 }, // Seoul, South Korea
          zoom: 10,
        };
      case 'TH':
        return {
          center: { lat: 13.7563, lng: 100.5018 }, // Bangkok, Thailand
          zoom: 10,
        };
      default:
        return { center: { lat: 36.5184, lng: 126.8 }, zoom: 5 };
    }
  }, [profile]);

  const [zoomLevel, setZoomLevel] = useState<number>(mapCenterByCountry.zoom);
  const [centerMap, setCenterMap] = useState(mapCenterByCountry.center);

  // Update map center and zoom when profile changes
  useEffect(() => {
    // Only update if there are no markers, to avoid interfering with auto-centering
    if (markerData?.length === 0) {
      const newCenter = mapCenterByCountry.center;
      const newZoom = mapCenterByCountry.zoom;

      // Only update if values have actually changed to prevent infinite loops
      if (
        centerMap.lat !== newCenter.lat ||
        centerMap.lng !== newCenter.lng ||
        zoomLevel !== newZoom
      ) {
        setCenterMap(newCenter);
        setZoomLevel(newZoom);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    profile?.group__settings?.use_map?.country_code,
    profile?.group__settings?.use_map?.select_map?.google_map,
    markerData,
  ]);

  // Use drawing hook
  const {
    mode: drawingMode,
    points: drawingPoints,
    currentShape,
    isDrawingActive,
    dragStartPoint,
    dragCurrentPoint,
    setMode: setDrawingMode,
    setPoints: setDrawingPoints,
    setCurrentShape,
    setIsDrawingActive,
    setDragStartPoint,
    setDragCurrentPoint,
    clearDrawing,
  } = useDrawing();

  // Use drawing mode store
  const setStoreDrawingMode = useDrawingModeStore(
    (state) => state.setDrawingMode,
  );
  const setStoreCurrentShape = useDrawingModeStore(
    (state) => state.setCurrentShape,
  );
  const storeCurrentShape = useDrawingModeStore((state) => state.currentShape);

  // Update store when drawing mode changes
  useEffect(() => {
    setStoreDrawingMode(drawingMode);
  }, [drawingMode, setStoreDrawingMode]);

  // Save shape to store when currentShape changes
  useEffect(() => {
    setStoreCurrentShape(currentShape);
  }, [currentShape, setStoreCurrentShape]);

  // Sync from store to local state when component mounts or store changes
  useEffect(() => {
    if (storeCurrentShape && !currentShape) {
      // If store has a shape but local state doesn't, restore it
      setCurrentShape(storeCurrentShape);
    }
  }, [storeCurrentShape, currentShape, setCurrentShape]);

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

    // Filter out invalid coordinates
    const validMarkerData = markerData.filter(
      (marker) =>
        marker.lat !== 0 &&
        marker.lng !== 0 &&
        !isNaN(marker.lat) &&
        !isNaN(marker.lng),
    );

    if (validMarkerData.length === 0) {
      isUpdatingRef.current = false;
      return;
    }

    // Check if we need to update the center/zoom to avoid unnecessary re-renders
    const currentCenter = centerMap;
    const currentZoom = zoomLevel;

    if (validMarkerData.length === 1) {
      const lat =
        Number(String(validMarkerData[0].lat).replace(',', '.')) || 37.5665;
      const lng =
        Number(String(validMarkerData[0].lng).replace(',', '.')) || 126.978;

      // Only update if the center has actually changed
      if (
        Math.abs(currentCenter.lat - lat) > 0.0001 ||
        Math.abs(currentCenter.lng - lng) > 0.0001 ||
        currentZoom !== 10
      ) {
        setCenterMap({ lat, lng });
        setZoomLevel(10);
      }
      isUpdatingRef.current = false;
      return;
    }

    // Use Google Maps equivalent of Kakao's center calculation
    const { center: calculatedCenter, zoom: calculatedZoom } =
      getGeographicCenterAndZoomGoogle({
        stops: validMarkerData,
        map: map,
      });

    if (calculatedCenter && calculatedZoom) {
      // Only update if the center/zoom has actually changed
      if (
        Math.abs(currentCenter.lat - calculatedCenter.lat) > 0.0001 ||
        Math.abs(currentCenter.lng - calculatedCenter.lng) > 0.0001 ||
        Math.abs(currentZoom - calculatedZoom) > 0.1
      ) {
        setCenterMap(calculatedCenter);
        setZoomLevel(calculatedZoom);
      }
    }

    isUpdatingRef.current = false;
  }, [map, markerData, centerMap, zoomLevel, setCenterMap, setZoomLevel]);

  useEffect(() => {
    if (!map || !markerData || markerData.length === 0 || isUpdatingRef.current)
      return;

    // Filter out invalid coordinates
    const validMarkerData = markerData.filter(
      (marker) =>
        marker.lat !== 0 &&
        marker.lng !== 0 &&
        !isNaN(marker.lat) &&
        !isNaN(marker.lng),
    );

    if (validMarkerData.length === 0) return;

    // Check if markerData has actually changed
    const hasMarkerDataChanged =
      prevMarkerDataRef.current.length !== validMarkerData.length ||
      prevMarkerDataRef.current.some((prevMarker, index) => {
        const currentMarker = validMarkerData[index];
        return (
          !currentMarker ||
          prevMarker.lat !== currentMarker.lat ||
          prevMarker.lng !== currentMarker.lng
        );
      });

    if (!hasMarkerDataChanged) return;

    // Update the ref to track current markerData
    prevMarkerDataRef.current = [...validMarkerData];

    // Use requestAnimationFrame for better performance than setTimeout
    const timeoutId = requestAnimationFrame(() => {
      setTimeout(() => {
        updateMapView();
      }, 2000);
    });

    return () => {
      cancelAnimationFrame(timeoutId);
      isUpdatingRef.current = false;
    };
  }, [map, markerData, updateMapView]);

  // Add mouse move listener for drawing preview when actively drawing
  useEffect(() => {
    if (
      !map ||
      !isDrawingActive ||
      !['POLYGON', 'CIRCULAR', 'TRACE'].includes(drawingMode)
    )
      return;

    let animationFrameId: number | null = null;
    let lastUpdateTime = 0;
    const THROTTLE_MS = 16; // ~60fps
    let isUpdating = false;

    const handleMouseMove = (e: google.maps.MapMouseEvent): void => {
      if (isDrawingActive && e.latLng && !isUpdating) {
        const now = Date.now();

        // Throttle updates for better performance
        if (now - lastUpdateTime < THROTTLE_MS) {
          return;
        }

        isUpdating = true;

        // Use requestAnimationFrame for smooth updates
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId);
        }

        animationFrameId = requestAnimationFrame(() => {
          if (e.latLng) {
            const lat = e.latLng.lat();
            const lng = e.latLng.lng();
            const currentPoint: DrawingPoint = { lat, lng };
            setDragCurrentPoint(currentPoint);
            lastUpdateTime = now;
          }
          isUpdating = false;
        });
      }
    };

    const listener = map.addListener('mousemove', handleMouseMove);

    return () => {
      if (listener) {
        google.maps.event.removeListener(listener);
      }
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      isUpdating = false;
    };
  }, [map, drawingMode, isDrawingActive, setDragCurrentPoint]);

  const handleCameraChange = useCallback(
    (ev: MapCameraChangedEvent) => {
      setCenterMap(ev.detail.center);
      setZoomLevel(ev.detail.zoom);
    },
    [setCenterMap, setZoomLevel],
  );

  // Use map click handler hook
  const { handleMapClick: handleKakaoMapClick, handleMapRightClick } =
    useMapClickHandler({
      drawingMode,
      drawingPoints,
      isDrawingActive,
      dragStartPoint,
      setDrawingPoints,
      setCurrentShape,
      setDrawingMode,
      setIsDrawingActive,
      setDragStartPoint,
      setDragCurrentPoint,
    });

  // Convert Google Maps MapMouseEvent to Kakao Maps MouseEvent format
  const handleMapClick = useCallback(
    (event: MapMouseEvent) => {
      if (!event.detail.latLng) return;

      // Create a mock MouseEvent object that matches Kakao Maps format
      const mockMouseEvent = {
        latLng: {
          getLat: () => event.detail.latLng!.lat,
          getLng: () => event.detail.latLng!.lng,
        },
      } as kakao.maps.event.MouseEvent;

      handleKakaoMapClick(mockMouseEvent);
    },
    [handleKakaoMapClick],
  );

  // Add right click listener for drawing
  useEffect(() => {
    if (!map) return;

    const handleRightClick = (): void => {
      handleMapRightClick();
    };

    const listener = map.addListener('rightclick', handleRightClick);

    return () => {
      if (listener) {
        google.maps.event.removeListener(listener);
      }
    };
  }, [map, handleMapRightClick]);

  return (
    <div
      style={{
        width: '100%',
        position: 'relative',
        borderRadius: 8,
        ...style,
        height: style?.height || '500px',
      }}
    >
      <GoogleMapWrapper
        $isDark={theme === 'dark'}
        style={{
          width: '100%',
          height: '100%',
          borderRadius: 8,
        }}
      >
        {/* Drawing Toolbar */}
        {!notUseActionButtons && (
          <DrawingToolbar
            drawingMode={drawingMode}
            handleDrawingModeChange={setDrawingMode}
            handleClearDrawing={clearDrawing}
          />
        )}

        <Map
          center={centerMap}
          zoom={zoomLevel}
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
          mapTypeControl={true}
          mapTypeControlOptions={{
            position: ControlPosition.TOP_RIGHT,
          }}
          cameraControl={false}
          zoomControl={true}
          zoomControlOptions={{
            position: ControlPosition.TOP_LEFT,
          }}
          keyboardShortcuts={false}
          colorScheme={theme === 'dark' ? ColorScheme.DARK : ColorScheme.LIGHT}
          gestureHandling="cooperative"
        >
          {/* Route Polyline - Draw white line connecting markers */}
          <RoutePolyline
            markerData={markerData}
            // strokeColor="#ffffff"
            strokeWeight={3}
            strokeOpacity={0.8}
            geodesic={true}
            isLineMode={isLineMode}
            onMarkerClick={onMarkerClick}
            droneRoutes={droneRoutes}
          />

          {/* Drawing Renderer */}
          <DrawingRenderer
            shapes={storeCurrentShape ? [storeCurrentShape] : []}
            drawingMode={drawingMode}
            drawingPoints={drawingPoints}
            isDrawingActive={isDrawingActive}
            dragStartPoint={dragStartPoint}
            dragCurrentPoint={dragCurrentPoint}
            markerData={markerData}
          />
        </Map>
        {overlayContent && overlayContent}
      </GoogleMapWrapper>
    </div>
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
