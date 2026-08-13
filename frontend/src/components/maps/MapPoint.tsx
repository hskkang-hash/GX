import React from 'react';
import { useConfigGroupSystem } from 'rj-core';

import { MAP_CONFIG } from '../../configs/Constant';
import MapGooglePoint from './MapGooglePoint';
import MapKakaoPoint from './MapKakaoPoint';

// Re-export types for convenience
export type { MarkerData, PolylineOptions, MapBounds } from './MapKakaoPoint';

// Unified map props interface
export interface MapPointProps {
  center?: { lat: number; lng: number };
  level?: number;
  operatingMarkers?: Array<{
    lat: number;
    lng: number;
    name?: string;
    icon?: string;
    terminal_name?: string;
  }>;
  standbyMarkers?: Array<{
    lat: number;
    lng: number;
    name?: string;
    icon?: string;
    terminal_name?: string;
  }>;
  polylines?: Array<{
    path: Array<{ lat: number; lng: number }>;
    strokeColor?: string;
    strokeOpacity?: number;
    strokeStyle?: 'solid' | 'shortdash' | 'shortdot';
    strokeWeight?: number;
    type?: 'DRONE' | 'ROBOT';
  }>;
  style?: React.CSSProperties;
  overlayContent?: React.ReactNode;
  smallMarker?: boolean;
  bounds?: {
    sw: { lat: number; lng: number };
    ne: { lat: number; lng: number };
  };
  terminalAddress?: {
    droneStartAddress: { lat: number; lng: number; name: string };
    robotStartAddress: { lat: number; lng: number; name: string };
    droneEndAddress: { lat: number; lng: number; name: string };
    robotEndAddress: { lat: number; lng: number; name: string };
  };
}

/**
 * Unified MapPoint component that renders either Kakao Maps or Google Maps
 * based on the MAP_CONFIG.PROVIDER setting.
 *
 * Configuration:
 * - Set VITE_MAP_PROVIDER=kakao to use Kakao Maps (default)
 * - Set VITE_MAP_PROVIDER=google to use Google Maps
 * - Set VITE_GOOGLE_MAPS_API_KEY for Google Maps API key
 * - Set VITE_KAKAO_MAPS_API_KEY for Kakao Maps API key (if needed)
 */
const MapPoint: React.FC<MapPointProps> = (props) => {
  const { configGroupSystem } = useConfigGroupSystem();
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;
  if (isSystemUseGoogleMap || isEmptyConfigGroupSystem) {
    return (
      <MapGooglePoint
        {...props}
        apiKey={MAP_CONFIG.GOOGLE_MAPS_API_KEY}
      />
    );
  }

  // Default to Kakao Maps
  return <MapKakaoPoint {...props} />;
};

export default React.memo(MapPoint);
