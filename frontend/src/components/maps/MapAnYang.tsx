import React from 'react';
import { useConfigGroupSystem } from 'rj-core';

import { MAP_CONFIG } from '../../configs/Constant';
import MapGoogleAnYang from './MapGoogleAnYang';
import MapKakaoAnYang from './MapKakaoAnYang';

interface MapAnYangProps {
  centerTerminal?: { lat: number; lng: number } | null;
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
  polylines?: Array<{
    route_terminals: Array<{
      lat: number | null | undefined;
      lng: number | null | undefined;
      for_robot?: boolean;
    }>;
    color: string;
  }>;
  style?: React.CSSProperties;
  overlayContent?: React.ReactNode;
  smallMarker?: boolean;
  bounds?: {
    sw: { lat: number; lng: number };
    ne: { lat: number; lng: number };
  };
  fitBounds?: boolean; // Auto-calculate and fit bounds from markers
  boundsPadding?: number; // Padding percentage for auto-calculated bounds (default: 0.1 = 10%)
  contentOverlay?: React.ReactNode;
  routeColor?: string;
  polylineColor?: string;
  controlVisibility?: {
    [key: string]: boolean;
  };
}

const MapAnYang: React.FC<MapAnYangProps> = (props) => {
  const { configGroupSystem } = useConfigGroupSystem();
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;

  if (isSystemUseGoogleMap || isEmptyConfigGroupSystem) {
    return (
      <MapGoogleAnYang
        {...props}
        apiKey={MAP_CONFIG.GOOGLE_MAPS_API_KEY}
      />
    );
  }

  // Default to Kakao Maps - exclude onMapInteraction prop as it's not supported
  const { ...kakaoProps } = props;
  return (
    <MapKakaoAnYang
      {...kakaoProps}
      routeColor={props.routeColor?.replace('#', '')}
    />
  );
};

export default MapAnYang;
