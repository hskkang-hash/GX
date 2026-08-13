import {
  AdvancedMarker,
  InfoWindow,
  useAdvancedMarkerRef,
} from '@vis.gl/react-google-maps';
import React, { useState } from 'react';

import { AbnormalSignMessage } from '../hooks/useSurveillanceDashboard';

interface DetectionMarkersGoogleProps {
  /** Detection notifications with images and locations */
  detections: AbnormalSignMessage[];
  /** Whether theme is dark */
  isDarkTheme?: boolean;
  /** Google map instance for re-centering */
  map?: google.maps.Map | null;
  /** Externally controlled selected detection ID */
  selectedDetectionId?: string | number | null;
  /** Callback when selection changes internally (e.g., marker click) */
  onSelectionChange?: (detection: AbnormalSignMessage | null) => void;
}

/**
 * Component to render detection markers on Google Map.
 * Shows numbered markers for each detection with an image.
 * When clicked, shows an InfoWindow with the detected image.
 */
const DetectionMarkersGoogle: React.FC<DetectionMarkersGoogleProps> = ({
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

  // Re-center map when marker is clicked to show both marker and popup
  const handleMarkerClick = React.useCallback(
    (detection: AbnormalSignMessage, isCurrentlySelected: boolean) => {
      if (!map) return;

      const lat = detection.drone_location?.location?.latitude;
      const lng = detection.drone_location?.location?.longitude;

      if (lat === undefined || lng === undefined) return;

      const newSelection = isCurrentlySelected ? null : detection;

      if (!isCurrentlySelected) {
        // When opening popup, offset the center upward to show both marker and popup
        // Adjust latitude by approximately 0.002 degrees (~220m) upward
        const offsetLat = lat + 0.002;
        map.panTo({ lat: offsetLat, lng });
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
      // Close if clicking on the map (not on InfoWindow or marker)
      if (
        !target.closest('.gm-style-iw') &&
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
      setTimeout(() => {
        document.addEventListener('click', handleClickOutside);
      }, 100);
      return () => {
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
      const offsetLat = lat + 0.002;
      map.panTo({ lat: offsetLat, lng });
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
          <DetectionMarker
            key={detection.id}
            detection={detection}
            index={index}
            position={position}
            isSelected={isSelected}
            isDarkTheme={isDarkTheme}
            onSelect={() => {
              handleMarkerClick(detection, isSelected);
            }}
            onClose={() => {
              if (selectedDetectionId === undefined) {
                setInternalSelectedDetection(null);
              }
              onSelectionChange?.(null);
            }}
          />
        );
      })}
    </>
  );
};

interface DetectionMarkerProps {
  detection: AbnormalSignMessage;
  index: number;
  position: { lat: number; lng: number };
  isSelected: boolean;
  isDarkTheme: boolean;
  onSelect: () => void;
  onClose: () => void;
}

const DetectionMarker: React.FC<DetectionMarkerProps> = ({
  detection,
  index,
  position,
  isSelected,
  isDarkTheme,
  onSelect,
  onClose,
}) => {
  const [markerRef, marker] = useAdvancedMarkerRef();

  return (
    <>
      <AdvancedMarker
        ref={markerRef}
        position={position}
        onClick={onSelect}
        title={detection.message}
      >
        {/* Custom marker with number */}
        <div
          data-detection-marker
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
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          {index + 1}
        </div>
      </AdvancedMarker>

      {/* InfoWindow with detection image only */}
      {isSelected && marker && (
        <InfoWindow
          anchor={marker}
          onCloseClick={onClose}
          headerDisabled={true}
        >
          <div
            className="gm-style-iw"
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '300px',
              padding: 0,
              margin: 0,
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
                borderRadius: '0.25rem',
                // Reverse parent map filter to show image in original colors
                filter: isDarkTheme ? 'hue-rotate(-180deg) invert(1)' : 'none',
              }}
              onError={(e) => {
                // Fallback if image fails to load
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        </InfoWindow>
      )}
    </>
  );
};

export default React.memo(DetectionMarkersGoogle);
