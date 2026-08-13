import React from 'react';
import { useConfigGroupSystem } from 'rj-core';

import { MAP_CONFIG } from '@/configs/Constant';

import { AbnormalSignMessage } from '../hooks/useSurveillanceDashboard';
import { ProfilePolygonData } from '../mapsComponents/PolygonOverlay';
import SurveillanceMapGoogle from './SurveillanceMapGoogle';
import SurveillanceMapKakao from './SurveillanceMapKakao';

// Re-export ProfilePolygonData for convenience
export type { ProfilePolygonData };

interface SurveillanceMapDashboardProps {
  centerTerminal?: { lat: number; lng: number } | null;
  profiles: ProfilePolygonData[];
  isLoading?: boolean;
  style?: React.CSSProperties;
  onProfileClick?: (profile: ProfilePolygonData) => void;
  getMapRef?: (map: kakao.maps.Map | google.maps.Map) => void;
  /** Detection notifications with images to show as markers */
  detectionNotifications?: AbnormalSignMessage[];
  /** Externally controlled selected detection ID */
  selectedDetectionId?: string | number | null;
  /** Callback when selection changes internally (e.g., marker click) */
  onSelectionChange?: (detection: AbnormalSignMessage | null) => void;
}

const SurveillanceMapDashboard: React.FC<SurveillanceMapDashboardProps> = (
  props,
) => {
  const { configGroupSystem } = useConfigGroupSystem();
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;

  // Use Google Map if configured or if config is empty (default)
  if (isSystemUseGoogleMap || isEmptyConfigGroupSystem) {
    return <SurveillanceMapGoogle {...props} />;
  }

  // Otherwise use Kakao Map
  return <SurveillanceMapKakao {...props} />;
};

export default React.memo(SurveillanceMapDashboard);
