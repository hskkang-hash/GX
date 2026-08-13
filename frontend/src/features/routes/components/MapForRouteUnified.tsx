import React from 'react';
import { useConfigGroupSystem } from 'rj-core';

import { MAP_CONFIG } from '../../../configs/Constant';
import MapForRoute from './MapForRoute';
import MapForRouteGoogle from './MapForRouteGoogle';

type Marker = {
  lat: number;
  lng: number;
  name?: string;
  for_robot?: boolean;
  color?: string;
};

type Props = {
  routeGroups?: { name?: string; lat: number; lng: number }[][];
  markerData?: Marker[];
  height?: string;
  dronePosition?: {
    lat: number;
    lng: number;
  };
  iconDrone?: string;
  style?: React.CSSProperties;
  useAddLocation?: boolean;
  handleAddLocation?: (position: { lat: number; lng: number }) => void;
  getMapRef?: (map: kakao.maps.Map | google.maps.Map) => void;
  onMarkerClick?: (marker: Marker) => void;
};

/**
 * Unified MapForRoute component that renders either Kakao Maps or Google Maps
 * based on the MAP_CONFIG.PROVIDER setting.
 *
 * Configuration:
 * - Set VITE_MAP_PROVIDER=kakao to use Kakao Maps (default)
 * - Set VITE_MAP_PROVIDER=google to use Google Maps
 * - Set VITE_GOOGLE_MAPS_API_KEY for Google Maps API key
 * - Set VITE_KAKAO_MAPS_API_KEY for Kakao Maps API key (if needed)
 */
const MapForRouteUnified: React.FC<Props> = (props) => {
  const { configGroupSystem } = useConfigGroupSystem();
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;
  if (isSystemUseGoogleMap || isEmptyConfigGroupSystem) {
    return (
      <MapForRouteGoogle
        {...props}
        apiKey={MAP_CONFIG.GOOGLE_MAPS_API_KEY}
        getMapRef={
          props.getMapRef as ((map: google.maps.Map) => void) | undefined
        }
      />
    );
  }

  // Default to Kakao Maps
  return (
    <MapForRoute
      {...props}
      getMapRef={props.getMapRef as ((map: kakao.maps.Map) => void) | undefined}
    />
  );
};

export default React.memo(MapForRouteUnified);
