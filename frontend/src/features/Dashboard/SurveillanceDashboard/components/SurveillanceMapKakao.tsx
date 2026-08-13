import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Map } from 'react-kakao-maps-sdk';
import { useTheme } from 'rj-core';
import styled from 'styled-components';

import { getGeographicCenterAndZoomKakaoByCenter } from '../../utils/calculateCenterAndZoom';
import { AbnormalSignMessage } from '../hooks/useSurveillanceDashboard';
import PolygonOverlayKakao, {
  ProfilePolygonData,
} from '../mapsComponents/PolygonOverlayKakao';
import DetectionMarkersKakao from './DetectionMarkersKakao';

const MapWrapper = styled.div<{ $isDark?: boolean }>`
  border-radius: 0.75rem;
  overflow: hidden;
  width: 100%;
  height: 100%;
  position: relative;

  /* Apply filter to wrapper instead of Map component to prevent re-renders */
  filter: ${(props) =>
    props.$isDark
      ? 'invert(1.5) hue-rotate(180deg)'
      : 'invert(0) hue-rotate(0deg)'};
`;

const LoadingOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.75rem;
  z-index: 100;
`;

const Spinner = styled.div`
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #3b82f6;
  animation: spin 1s ease-in-out infinite;

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
`;

const MapControls = styled.div`
  position: absolute;
  top: 1rem;
  left: 1rem;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`;

const ControlButton = styled.button<{ $isDark?: boolean }>`
  width: 2.5rem;
  height: 2.5rem;
  background: ${(props) =>
    props.$isDark ? 'rgba(31, 41, 55, 0.95)' : 'rgba(255, 255, 255, 0.95)'};
  border: 1px solid ${(props) => (props.$isDark ? '#374151' : '#e5e7eb')};
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: ${(props) => (props.$isDark ? '#f9fafb' : '#111827')};

  &:hover {
    background: ${(props) =>
      props.$isDark ? 'rgba(55, 65, 81, 0.95)' : 'rgba(229, 231, 235, 0.95)'};
  }

  svg {
    width: 1.25rem;
    height: 1.25rem;
  }
`;

interface SurveillanceMapKakaoProps {
  centerTerminal?: { lat: number; lng: number } | null;
  profiles: ProfilePolygonData[];
  isLoading?: boolean;
  style?: React.CSSProperties;
  /** Detection notifications with images to show as markers */
  detectionNotifications?: AbnormalSignMessage[];
  /** Externally controlled selected detection ID */
  selectedDetectionId?: string | number | null;
  /** Callback when selection changes internally (e.g., marker click) */
  onSelectionChange?: (detection: AbnormalSignMessage | null) => void;
}

const SurveillanceMapKakao: React.FC<SurveillanceMapKakaoProps> = ({
  centerTerminal,
  profiles,
  isLoading,
  style,
  detectionNotifications = [],
  selectedDetectionId,
  onSelectionChange,
}) => {
  const internalMapRef = useRef<kakao.maps.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [hasInitialized, setHasInitialized] = useState(false);
  const [zoomLevel, setZoomLevel] = useState<number>(13);
  const [centerMap, setCenterMap] = useState<{ lat: number; lng: number }>({
    lat: 35.4152,
    lng: 127.5283,
  });
  const [mapInstance, setMapInstance] = useState<kakao.maps.Map | null>(null);
  const [theme] = useTheme();
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(
    null,
  );

  useEffect(() => {
    if (!centerTerminal?.lat || !centerTerminal?.lng) {
      return;
    }
    const map = internalMapRef.current;
    if (!map || !mapReady) {
      return;
    }
    const { center: centerMapInstance, zoom } =
      getGeographicCenterAndZoomKakaoByCenter({
        stop: { lat: centerTerminal.lat, lng: centerTerminal.lng },
        map: map,
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

  const handleZoomIn = useCallback(() => {
    if (mapInstance) {
      const currentLevel = mapInstance.getLevel();
      const newLevel = Math.max(1, currentLevel - 1);
      mapInstance.setLevel(newLevel);
      setZoomLevel(newLevel);
    }
  }, [mapInstance]);

  const handleZoomOut = useCallback(() => {
    if (mapInstance) {
      const currentLevel = mapInstance.getLevel();
      const newLevel = Math.min(14, currentLevel + 1);
      mapInstance.setLevel(newLevel);
      setZoomLevel(newLevel);
    }
  }, [mapInstance]);

  const isDarkTheme = theme === 'dark';

  // Force markers to re-render when theme changes
  React.useEffect(() => {
    if (mapInstance && mapReady) {
      // Trigger a small update to force marker re-render
      const currentCenter = mapInstance.getCenter();
      mapInstance.panTo(currentCenter);
    }
  }, [isDarkTheme, mapInstance, mapReady]);

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        borderRadius: '0.75rem',
        ...style,
      }}
    >
      <MapWrapper $isDark={isDarkTheme}>
        <MapControls>
          <ControlButton
            $isDark={isDarkTheme}
            onClick={handleZoomIn}
            title="Zoom In"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line
                x1="12"
                y1="5"
                x2="12"
                y2="19"
              ></line>
              <line
                x1="5"
                y1="12"
                x2="19"
                y2="12"
              ></line>
            </svg>
          </ControlButton>
          <ControlButton
            $isDark={isDarkTheme}
            onClick={handleZoomOut}
            title="Zoom Out"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line
                x1="5"
                y1="12"
                x2="19"
                y2="12"
              ></line>
            </svg>
          </ControlButton>
        </MapControls>

        <Map
          center={centerMap}
          level={zoomLevel}
          isPanto={true}
          style={{
            width: '100%',
            height: '100%',
            borderRadius: '0.75rem',
          }}
          onCreate={(map) => {
            internalMapRef.current = map;
            setMapInstance(map);
            setMapReady(true);
          }}
          onCenterChanged={(map) => {
            const latlng = map.getCenter();
            setCenterMap({ lat: latlng.getLat(), lng: latlng.getLng() });
          }}
          onZoomChanged={(map) => {
            setZoomLevel(map.getLevel());
          }}
        >
          <PolygonOverlayKakao
            map={mapInstance}
            profiles={profiles}
            selectedProfileId={selectedProfileId}
            isDarkTheme={isDarkTheme}
          />

          {/* Detection markers for abnormal signs with images */}
          <DetectionMarkersKakao
            key={`detection-markers-${isDarkTheme ? 'dark' : 'light'}`}
            detections={detectionNotifications}
            isDarkTheme={isDarkTheme}
            map={mapInstance}
            selectedDetectionId={selectedDetectionId}
            onSelectionChange={onSelectionChange}
          />
        </Map>
      </MapWrapper>

      {isLoading && (
        <LoadingOverlay>
          <Spinner />
        </LoadingOverlay>
      )}
    </div>
  );
};

export default React.memo(SurveillanceMapKakao);
