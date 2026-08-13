import {
  APIProvider,
  ColorScheme,
  ControlPosition,
  Map,
  MapCameraChangedEvent,
  useMap,
} from '@vis.gl/react-google-maps';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useProfile, useTheme } from 'rj-core';
import styled from 'styled-components';

import { MAP_CONFIG } from '@/configs/Constant';

import { AbnormalSignMessage } from '../hooks/useSurveillanceDashboard';
import PolygonOverlay, {
  ProfilePolygonData,
} from '../mapsComponents/PolygonOverlay';
import { getGeographicCenterAndZoomGoogleByCenter } from '../../utils/calculateCenterAndZoom';
import DetectionMarkersGoogle from './DetectionMarkersGoogle';

const GoogleMapWrapper = styled.div<{ $isDark?: boolean }>`
  border-radius: 0.75rem;
  overflow: hidden;
  width: 100%;
  height: 100%;

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
      border-radius: 0.75rem;
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

  .gm-ui-hover-effect {
    border-radius: 50% !important;
    opacity: ${(props) => (props.$isDark ? '0.9' : '0.8')} !important;

    &:hover {
      background-color: ${(props) =>
    props.$isDark ? '#4b5563' : '#e5e7eb'} !important;
      opacity: 1 !important;
    }
  }

  .gm-style-iw-tc::after {
    background-color: ${(props) =>
    props.$isDark ? '#1f2937' : '#ffffff'} !important;
    border-color: ${(props) =>
    props.$isDark ? '#374151' : '#e5e7eb'} !important;
  }
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

interface SurveillanceMapGoogleProps {
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

interface MapContentProps extends Omit<SurveillanceMapGoogleProps, 'style'> {
  style?: React.CSSProperties;
}

const SurveillanceMapContent: React.FC<MapContentProps> = ({
  centerTerminal,
  profiles,
  isLoading,
  style,
  detectionNotifications = [],
  selectedDetectionId,
  onSelectionChange,
}) => {
  const [theme] = useTheme();
  const { profile } = useProfile();
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null);
  const map = useMap();

  const mapCenterByCountry = useMemo(() => {
    const isGoogleMap = profile?.group__settings?.use_map?.select_map?.google_map;
    const countryCode = profile?.group__settings?.use_map?.country_code;

    if (!isGoogleMap) {
      return { center: { lat: 37.3947, lng: 126.9568 }, zoom: 14 };
    }

    switch (countryCode) {
      case 'KR':
        return { center: { lat: 37.3947, lng: 126.9568 }, zoom: 14 };
      case 'TH':
        return { center: { lat: 13.7563, lng: 100.5018 }, zoom: 12 };
      default:
        return { center: { lat: 37.3947, lng: 126.9568 }, zoom: 14 };
    }
  }, [profile]);

  const [zoomLevel, setZoomLevel] = useState<number>(mapCenterByCountry.zoom);
  const [centerMap, setCenterMap] = useState(mapCenterByCountry.center);

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
          setCenterMap(calculatedCenter);
          setZoomLevel(calculatedZoom);
        }
      } else {
        setCenterMap({
          lat: centerTerminal.lat,
          lng: centerTerminal.lng,
        });
        setZoomLevel(15);
      }
    }
  }, [centerTerminal, map]);

  const handleCameraChange = useCallback((ev: MapCameraChangedEvent) => {
    setCenterMap(ev.detail.center);
    setZoomLevel(ev.detail.zoom);
  }, []);

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
      <GoogleMapWrapper $isDark={theme === 'dark'} style={{ width: '100%', height: '100%' }}>
        <Map
          center={centerMap}
          zoom={zoomLevel}
          mapId="surveillance-dashboard-map"
          style={{ width: '100%', height: '100%', borderRadius: '0.75rem' }}
          onCameraChanged={handleCameraChange}
          streetViewControl={false}
          fullscreenControl={true}
          fullscreenControlOptions={{ position: ControlPosition.BOTTOM_LEFT }}
          mapTypeControl={true}
          mapTypeControlOptions={{ position: ControlPosition.TOP_RIGHT }}
          mapTypeId="roadmap"
          cameraControl={false}
          zoomControl={true}
          zoomControlOptions={{ position: ControlPosition.TOP_LEFT }}
          keyboardShortcuts={false}
          colorScheme={theme === 'dark' ? ColorScheme.DARK : ColorScheme.LIGHT}
          gestureHandling="cooperative"
        >
          <PolygonOverlay profiles={profiles} selectedProfileId={selectedProfileId} />

          {/* Detection markers for abnormal signs with images */}
          <DetectionMarkersGoogle
            detections={detectionNotifications}
            isDarkTheme={theme === 'dark'}
            map={map}
            selectedDetectionId={selectedDetectionId}
            onSelectionChange={onSelectionChange}
          />
        </Map>
      </GoogleMapWrapper>

      {isLoading && (
        <LoadingOverlay>
          <Spinner />
        </LoadingOverlay>
      )}
    </div>
  );
};

const SurveillanceMapGoogle: React.FC<SurveillanceMapGoogleProps> = (props) => {
  const { i18n } = useTranslation();
  const currentLanguage = i18n.language;

  return (
    <APIProvider
      apiKey={MAP_CONFIG.GOOGLE_MAPS_API_KEY}
      language={currentLanguage === 'en' ? 'en' : 'ko'}
    >
      <SurveillanceMapContent {...props} />
    </APIProvider>
  );
};

export default React.memo(SurveillanceMapGoogle);
