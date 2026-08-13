import React from 'react';
import { useConfigGroupSystem } from 'rj-core';

import { MAP_CONFIG } from '../../configs/Constant';
import MapGoogle from './MapGoogle';
import MapKakao from './MapKakao';

// Re-export types for convenience
export type { MarkerData, PolylinePath, MapBounds } from './MapKakao';

// Unified map props interface (excluding provider-specific props)
export interface MapProps {
  centerTerminal?: { lat: number; lng: number } | null;
  center?: { lat: number; lng: number };
  level?: number;
  operatingMarkers?: Array<{
    lat: number | null | undefined;
    lng: number | null | undefined;
    name?: string;
    icon?: string;
    terminal_name?: string;
  }>;
  standbyMarkers?: Array<{
    lat: number | null | undefined;
    lng: number | null | undefined;
    name?: string;
    icon?: string;
    terminal_name?: string;
  }>;
  droneMarkers?: Array<{
    lat: number | null | undefined;
    lng: number | null | undefined;
    name?: string;
    icon?: string;
    terminal_name?: string;
  }>;
  polylines?: Array<
    Array<{
      lat: number | null | undefined;
      lng: number | null | undefined;
      for_robot?: boolean;
    }>
  >;
  style?: React.CSSProperties;
  overlayContent?: React.ReactNode;
  smallMarker?: boolean;
  bounds?: {
    sw: { lat: number; lng: number };
    ne: { lat: number; lng: number };
  };
  fitBounds?: boolean;
  boundsPadding?: number;
  onMapInteraction?: () => void;
}

/**
 * Unified Map component that renders either Kakao Maps or Google Maps
 * based on the MAP_CONFIG.PROVIDER setting.
 *
 * Configuration:
 * - Set VITE_MAP_PROVIDER=kakao to use Kakao Maps (default)
 * - Set VITE_MAP_PROVIDER=google to use Google Maps
 * - Set VITE_GOOGLE_MAPS_API_KEY for Google Maps API key
 * - Set VITE_KAKAO_MAPS_API_KEY for Kakao Maps API key (if needed)
 */
const Map: React.FC<MapProps> = (props) => {
  const { configGroupSystem } = useConfigGroupSystem();
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;

  if (isSystemUseGoogleMap || isEmptyConfigGroupSystem) {
    return (
      <MapGoogle
        {...props}
        apiKey={MAP_CONFIG.GOOGLE_MAPS_API_KEY}
      />
    );
  }

  // Default to Kakao Maps - exclude onMapInteraction prop as it's not supported
  const { ...kakaoProps } = props;
  return <MapKakao {...kakaoProps} />;
};

export default React.memo(Map);
