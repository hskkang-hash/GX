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
  routeId?: string | number;
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
  overlayContent?: React.ReactNode;
  handleAddLocation?: (position: { lat: number; lng: number }) => void;
  getMapRef?: (map: kakao.maps.Map | google.maps.Map) => void;
  isLineMode?: boolean;
  notUseActionButtons?: boolean;
  onMarkerClick?: (marker: Marker) => void;
};

const MapForRouteUnified = (props: Props) => {
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

  return (
    <MapForRoute
      {...props}
      getMapRef={props.getMapRef as ((map: kakao.maps.Map) => void) | undefined}
    />
  );
};

export default MapForRouteUnified;
