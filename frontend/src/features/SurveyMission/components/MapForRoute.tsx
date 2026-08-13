import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Map } from 'react-kakao-maps-sdk';
import { useTheme } from 'rj-core';

import { getGeographicCenterAndZoomKakao } from '../../routes/utils/calculateCenterAndZoom';
import { useDrawingModeStore } from '../stores/drawingModeStore';
import RoutePolylineKakao from './RoutePolylineKakao';
import {
  DrawingRenderer,
  DrawingToolbar,
  MapControls,
  useDrawing,
  useMapClickHandler,
} from './drawing';
import { log } from 'console';

type Marker = {
  lat: number;
  lng: number;
  name?: string;
  for_robot?: boolean;
  color?: string;
  routeId?: string | number;
};

type Props = {
  markerData?: Marker[];
  style?: React.CSSProperties;
  overlayContent?: React.ReactNode;
  getMapRef?: (map: kakao.maps.Map) => void;
  isLineMode?: boolean;
  notUseActionButtons?: boolean;
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

const MapForRoute = ({
  markerData = [],
  style = {},
  overlayContent,
  isLineMode = false,
  notUseActionButtons = false,
  onMarkerClick,
}: Props) => {
  const mapRef = useRef<kakao.maps.Map | null>(null);
  const isUpdatingRef = useRef(false);
  const prevMarkerDataRef = useRef<Marker[]>([]);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const [theme] = useTheme();
  const [overlayType, setOverlayType] = useState<OverlayType>('NONE');
  const [zoomLevel, setZoomLevel] = useState<number>(3);
  const [centerMap, setCenterMap] = useState({
    lat: 37.5665,
    lng: 126.978,
  });
  const [isFullscreen, setIsFullscreen] = useState(false);

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

  useEffect(() => {
    if (typeof kakao === 'undefined') {
      return;
    }
  }, []);

  // Auto-center map based on marker data - only run when markers actually change
  const updateMapView = useCallback((): void => {
    if (isUpdatingRef.current || !mapRef.current) return;

    isUpdatingRef.current = true;

    // Check if we need to update the center/zoom to avoid unnecessary re-renders
    const currentCenter = centerMap;
    const currentZoom = zoomLevel;

    if (markerData.length === 1) {
      const lat =
        Number(String(markerData[0].lat).replace(',', '.')) || 37.5665;
      const lng =
        Number(String(markerData[0].lng).replace(',', '.')) || 126.978;

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
      }
    }

    isUpdatingRef.current = false;
  }, [markerData, centerMap, zoomLevel, setCenterMap, setZoomLevel]);

  useEffect(() => {
    if (!markerData || markerData.length === 0 || isUpdatingRef.current) return;

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
  }, [markerData, updateMapView]);

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

  // Use map click handler hook
  const { handleMapClick, handleMapRightClick } = useMapClickHandler({
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

  // Add mouse move listener for drawing preview when actively drawing
  useEffect(() => {
    const map = mapRef.current;
    if (
      !map ||
      !isDrawingActive ||
      !['POLYGON', 'CIRCULAR', 'TRACE'].includes(drawingMode)
    )
      return;

    const handleMouseMove = (e: kakao.maps.event.MouseEvent): void => {
      if (isDrawingActive) {
        const latlng = e.latLng;
        const currentPoint = {
          lat: latlng.getLat(),
          lng: latlng.getLng(),
        };
        setDragCurrentPoint(currentPoint);
      }
    };

    kakao.maps.event.addListener(map, 'mousemove', handleMouseMove);

    return () => {
      kakao.maps.event.removeListener(map, 'mousemove', handleMouseMove);
    };
  }, [drawingMode, isDrawingActive, setDragCurrentPoint]);

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

  // Complete LINE drawing when clicking outside the map
  useEffect(() => {
    if (drawingMode !== 'LINE' || drawingPoints.length === 0) {
      return;
    }

    const handleClickOutside = (event: MouseEvent): void => {
      if (!mapContainerRef.current) return;

      // Check if click is outside the map container
      const target = event.target as Node;
      if (!mapContainerRef.current.contains(target)) {
        // Complete the line drawing by setting drawingMode to NONE
        // Only complete if we have at least 1 point (user has started drawing)
        if (drawingPoints.length >= 1) {
          setDrawingPoints([]);
          setDrawingMode('NONE');
        }
      }
    };

    // Add event listener to document
    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [drawingMode, drawingPoints.length, setDrawingMode, setDrawingPoints]);

  return (
    <div
      ref={mapContainerRef}
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

      {/* Drawing Toolbar */}
      {!notUseActionButtons && (
        <DrawingToolbar
          drawingMode={drawingMode}
          handleDrawingModeChange={setDrawingMode}
          handleClearDrawing={clearDrawing}
        />
      )}
      <div
        style={{
          width: '100%',
          height: '100%',
          position: 'relative',
        }}
      >
        <Map
          key={`map-${isFullscreen ? 'fullscreen' : 'normal'}-${theme}`}
          ref={mapRef}
          center={centerMap}
          level={zoomLevel}
          isPanto={true}
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
          onClick={(_, mouseEvent) => {
            handleMapClick(mouseEvent);
          }}
          onRightClick={() => {
            handleMapRightClick();
          }}
        >
          {/* Route Polyline - Calculate inverse color for dark theme to maintain white appearance */}
          <RoutePolylineKakao
            markerData={markerData}
            strokeColor={theme === 'dark' ? '#000000' : '#9C9D9D'}
            strokeWeight={3}
            strokeOpacity={0.8}
            strokeStyle="solid"
            isLineMode={isLineMode}
            onMarkerClick={onMarkerClick}
          />

          {/* Drawing Renderer - Colors will be automatically adjusted */}
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
      </div>
      {overlayContent && overlayContent}
    </div>
  );
};

export default React.memo(MapForRoute);
