import React, { useState } from 'react';
import { CustomOverlayMap } from 'react-kakao-maps-sdk';

import { AbnormalSignMessage } from '../hooks/useSurveillanceDashboard';

interface DetectionMarkersKakaoProps {
  /** Detection notifications with images and locations */
  detections: AbnormalSignMessage[];
  /** Whether theme is dark */
  isDarkTheme?: boolean;
  /** Kakao map instance for re-centering */
  map?: kakao.maps.Map | null;
  /** Externally controlled selected detection ID */
  selectedDetectionId?: string | number | null;
  /** Callback when selection changes internally (e.g., marker click) */
  onSelectionChange?: (detection: AbnormalSignMessage | null) => void;
}

/**
 * Component to render detection markers on Kakao Map.
 * Shows numbered markers for each detection with an image.
 * When clicked, shows a popup with the detected image.
 */
const DetectionMarkersKakao: React.FC<DetectionMarkersKakaoProps> = ({
  detections,
  isDarkTheme = false,
  map,
  selectedDetectionId,
  onSelectionChange,
}) => {
  const [internalSelectedDetection, setInternalSelectedDetection] =
    useState<AbnormalSignMessage | null>(null);

  // Use external selection if provided, otherwise use internal state
  const selectedDetection =
    selectedDetectionId !== undefined
      ? detections.find((d) => d.id === selectedDetectionId) || null
      : internalSelectedDetection;

  const handleMarkerClick = React.useCallback(
    (detection: AbnormalSignMessage, isCurrentlySelected: boolean) => {
      if (!map) return;

      const lat = detection.drone_location?.location?.latitude;
      const lng = detection.drone_location?.location?.longitude;

      if (lat === undefined || lng === undefined) return;

      const newSelection = isCurrentlySelected ? null : detection;

      if (!isCurrentlySelected) {
        const projection = map.getProjection();

        // Convert LatLng to pixel point
        const point = projection.pointFromCoords(
          new window.kakao.maps.LatLng(lat, lng),
        );

        // Move UP by 120px (decrease y)
        point.y -= 100;

        // Convert back to LatLng
        const newCenter = projection.coordsFromPoint(point);

        map.panTo(newCenter);
      }

      // Update internal state if not externally controlled
      if (selectedDetectionId === undefined) {
        setInternalSelectedDetection(newSelection);
      }

      // Notify parent of selection change
      onSelectionChange?.(newSelection);
    },
    [map, selectedDetectionId, onSelectionChange],
  );

  // Close popup when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      // Close if clicking on the map (not on popup or marker)
      if (
        !target.closest('[data-detection-popup]') &&
        !target.closest('[data-detection-marker]')
      ) {
        // Only handle if not externally controlled
        if (selectedDetectionId === undefined) {
          setInternalSelectedDetection(null);
        }
        onSelectionChange?.(null);
      }
    };

    if (selectedDetection) {
      // Small delay to prevent immediate close when opening
      const timeoutId = setTimeout(() => {
        document.addEventListener('click', handleClickOutside);
      }, 100);

      return () => {
        clearTimeout(timeoutId);
        document.removeEventListener('click', handleClickOutside);
      };
    }
  }, [selectedDetection, selectedDetectionId, onSelectionChange]);

  // Handle external selection changes - pan map when selection changes externally
  React.useEffect(() => {
    if (selectedDetectionId !== undefined && selectedDetection && map) {
      const lat = selectedDetection.drone_location?.location?.latitude;
      const lng = selectedDetection.drone_location?.location?.longitude;

      if (lat === undefined || lng === undefined) return;

      const projection = map.getProjection();
      const point = projection.pointFromCoords(
        new window.kakao.maps.LatLng(lat, lng),
      );
      point.y -= 100;
      const newCenter = projection.coordsFromPoint(point);
      map.panTo(newCenter);
    }
  }, [selectedDetectionId, selectedDetection, map]);

  // Filter detections that have both image and location
  const validDetections = detections.filter(
    (detection) =>
      detection.detected_image_path &&
      detection.drone_location?.location?.latitude &&
      detection.drone_location?.location?.longitude,
  );

  return (
    <>
      {validDetections.map((detection, index) => {
        const lat = detection.drone_location?.location?.latitude;
        const lng = detection.drone_location?.location?.longitude;

        if (lat === undefined || lng === undefined) return null;

        const position = {
          lat,
          lng,
        };

        const isSelected = selectedDetection?.id === detection.id;

        return (
          <React.Fragment key={detection.id}>
            {/* Custom marker with number */}
            <CustomOverlayMap
              position={position}
              yAnchor={1}
            >
              <div
                data-detection-marker
                style={{
                  position: 'relative',
                  cursor: 'pointer',
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleMarkerClick(detection, isSelected);
                }}
              >
                {/* Marker circle with number */}
                <div
                  style={{
                    width: '2.5rem',
                    height: '2.5rem',
                    borderRadius: '50%',
                    backgroundColor: '#2196F3',
                    border: isSelected ? '3px solid white' : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: 'bold',
                    fontSize: '1rem',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
                    transition: 'all 0.2s ease',
                    position: 'relative',
                  }}
                >
                  {index + 1}
                </div>
              </div>
            </CustomOverlayMap>

            {/* Image popup when marker is clicked - positioned above marker */}
            {isSelected && (
              <CustomOverlayMap
                position={position}
                yAnchor={1.2} // Position popup above the marker
              >
                {isSelected && (
                  <div
                    data-detection-popup
                    onClick={(e) => e.stopPropagation()}
                    style={{
                      // position: 'absolute',
                      // left: '50%',
                      // bottom: '100%',
                      // transform: 'translateX(-50%) translateY(-100%)',
                      width: '300px',
                      borderRadius: '0.5rem',
                      overflow: 'hidden',
                      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                      // Reverse parent map filter to show image in original colors
                      filter: isDarkTheme
                        ? 'hue-rotate(-180deg) invert(1)'
                        : 'none',
                    }}
                  >
                    {/* Detection image only */}
                    <img
                      src={detection.detected_image_path}
                      alt="Detection"
                      style={{
                        width: '100%',
                        height: 'auto',
                        maxHeight: '250px',
                        objectFit: 'cover',
                        display: 'block',
                        borderRadius: '0.5rem',
                      }}
                      onError={(e) => {
                        // Fallback if image fails to load
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                  </div>
                )}
              </CustomOverlayMap>
            )}
          </React.Fragment>
        );
      })}
    </>
  );
};

export default React.memo(DetectionMarkersKakao);
