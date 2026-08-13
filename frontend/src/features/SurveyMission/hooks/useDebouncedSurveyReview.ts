import { useCallback, useEffect, useRef, useState } from 'react';
import { useFormContext } from 'react-hook-form';

import { useDrawingModeStore } from '../stores/drawingModeStore';
import { Waypoint } from '../types/surveyMission.types';
import { useSurveyMission } from './useSurveyMission';

type SurveyData = {
  polygon: number[][];
  hover_and_capture: boolean;
  altitude: number;
  takeoff_altitude: number;
  altitude_separation: number;
  survey_angle: number;
  spacing: number;
  turnaround_distance: number;
  trigger_distance: number;
  overlap: number;
};

interface UseDebouncedSurveyReviewProps {
  data: SurveyData;
  delay?: number;
  enabled?: boolean;
  skipInitialCall?: boolean; // Skip API call on initial mount
}

interface WaypointResponse {
  latitude: number;
  longitude: number;
  cruise_speed?: number;
  operating_altitude?: number;
  command: {
    id: number;
    name: string;
  };
  frame: {
    id: number;
    name: string;
  };
  params: number[];
}

interface ReviewResponse {
  data?: {
    waypoints?: WaypointResponse[];
    visual_transect_points?: [number, number][];
    estimates?: {
      time_minutes?: number;
      distance_km?: number;
    };
  };
}

// Constants
const DEFAULT_CRUISE_SPEED = 50;
const DEFAULT_ALTITUDE = 10;
const DEFAULT_OPERATING_ALTITUDE_FALLBACK = 50;

// Deep comparison helper for SurveyData
const isSurveyDataEqual = (
  prev: SurveyData | null,
  next: SurveyData,
): boolean => {
  if (!prev) return false;

  // Compare primitive values
  if (
    prev.hover_and_capture !== next.hover_and_capture ||
    prev.altitude !== next.altitude ||
    prev.survey_angle !== next.survey_angle ||
    prev.spacing !== next.spacing ||
    prev.turnaround_distance !== next.turnaround_distance ||
    prev.trigger_distance !== next.trigger_distance ||
    prev.overlap !== next.overlap
  ) {
    return false;
  }

  // Compare polygon arrays
  if (prev.polygon.length !== next.polygon.length) {
    return false;
  }

  for (let i = 0; i < prev.polygon.length; i++) {
    if (prev.polygon[i].length !== next.polygon[i].length) {
      return false;
    }
    for (let j = 0; j < prev.polygon[i].length; j++) {
      if (prev.polygon[i][j] !== next.polygon[i][j]) {
        return false;
      }
    }
  }

  return true;
};

// Transform waypoint response to Waypoint format
const transformWaypoint = (
  waypoint: WaypointResponse,
  index: number,
  existingWaypoints: Waypoint[],
  defaultOperatingAltitude: number,
): Waypoint => {
  const existing = existingWaypoints[index];

  return {
    cruise_speed:
      existing?.cruise_speed ??
      String(waypoint?.cruise_speed ?? DEFAULT_CRUISE_SPEED),
    operating_altitude:
      existing?.operating_altitude ??
      String(waypoint?.operating_altitude ?? defaultOperatingAltitude),
    command: {
      label: waypoint.command.name,
      value: waypoint.command.id,
    },
    frame: {
      label: waypoint.frame.name,
      value: waypoint.frame.id,
    },
    param_1: waypoint.params[0] ?? 0,
    param_2: waypoint.params[1] ?? 0,
    param_3: waypoint.params[2] ?? 0,
    param_4: waypoint.params[3] ?? 0,
    param_5: waypoint.params[4] ?? 0,
    param_6: waypoint.params[5] ?? 0,
    latitude: waypoint.latitude ?? 0,
    longitude: waypoint.longitude ?? 0,
    altitude: waypoint.params[6] ?? DEFAULT_ALTITUDE,
    terminal__latitude: existing?.terminal__latitude ?? waypoint.params[4] ?? 0,
    terminal__longitude:
      existing?.terminal__longitude ?? waypoint.params[5] ?? 0,
    command_line: existing?.command_line,
  };
};

export const useDebouncedSurveyReview = ({
  data,
  delay = 1000,
  enabled = true,
  skipInitialCall = false,
}: UseDebouncedSurveyReviewProps) => {
  const { reviewSurveyMission } = useSurveyMission();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const previousDataRef = useRef<SurveyData | null>(null);
  const isInitialMountRef = useRef(true);
  const [isPending, setIsPending] = useState(false);
  const { setValue } = useFormContext();

  const setWaypointsPreview = useDrawingModeStore(
    (state) => state.setWaypointsPreview,
  );
  const setWaypointsList = useDrawingModeStore(
    (state) => state.setWaypointsList,
  );
  const waypointsList = useDrawingModeStore((state) => state.waypointsList);
  const qgcMissionData = useDrawingModeStore((state) => state.qgcMissionData);

  // Stable reference to waypointsList to avoid unnecessary re-renders
  const waypointsListRef = useRef<Waypoint[]>(waypointsList);
  useEffect(() => {
    waypointsListRef.current = waypointsList;
  }, [waypointsList]);

  const debouncedReview = useCallback(
    async (surveyData: SurveyData) => {
      setIsPending(true);
      try {
        const dataResponse = (await reviewSurveyMission({
          data: {
            polygon: surveyData.polygon as [][],
            hover_and_capture: surveyData.hover_and_capture,
            altitude: surveyData.altitude,
            takeoff_altitude: surveyData.takeoff_altitude,
            altitude_separation: surveyData.altitude_separation,
            survey_angle: surveyData.survey_angle,
            spacing: surveyData.spacing,
            turnaround_distance: surveyData.turnaround_distance,
            trigger_distance: surveyData.trigger_distance,
            frontal_overlap: surveyData.overlap,
            side_overlap: surveyData.overlap,
            entry_location: 1,
            cruise_speed: 10,
            hover_speed: 5,
          },
        })) as ReviewResponse | undefined;

        if (dataResponse?.data) {
          // Update preview points
          setWaypointsPreview(dataResponse.data.visual_transect_points || []);

          // Get current waypoints list at the time of execution
          const currentWaypointsList = waypointsListRef.current;

          // Transform waypoints
          const transformedWaypoints =
            dataResponse.data.waypoints?.map((waypoint, index) =>
              transformWaypoint(
                waypoint,
                index,
                currentWaypointsList,
                surveyData.altitude ?? DEFAULT_OPERATING_ALTITUDE_FALLBACK,
              ),
            ) || [];

          setWaypointsList(transformedWaypoints);

          // Update form values
          if (dataResponse.data.estimates) {
            setValue(
              'estimated_time',
              dataResponse.data.estimates.time_minutes,
            );
            setValue('total_distance', dataResponse.data.estimates.distance_km);
          }
        }
      } catch (error) {
        console.error('Error in debounced survey review:', error);
        setWaypointsPreview([]);
        throw error;
      } finally {
        setIsPending(false);
      }
    },
    [reviewSurveyMission, setWaypointsPreview, setWaypointsList, setValue],
  );

  useEffect(() => {
    // Skip if disabled, no data, or no polygon
    if (!enabled || !data || !data.polygon || data.polygon.length === 0) {
      setIsPending(false);
      return;
    }

    // If skipInitialCall is true and we haven't set previousDataRef yet (initial load from server),
    // set previousDataRef to current data without calling API
    // This handles both initial mount and when skipInitialCall becomes true after data loads
    if (skipInitialCall && !previousDataRef.current) {
      previousDataRef.current = data;
      setIsPending(false); // Ensure pending is false when skipping initial call
      if (isInitialMountRef.current) {
        isInitialMountRef.current = false;
      }
      return;
    }

    // Mark that initial mount is done
    if (isInitialMountRef.current) {
      isInitialMountRef.current = false;
    }

    // Check if data has actually changed using efficient deep comparison
    const hasChanged =
      !previousDataRef.current ||
      !isSurveyDataEqual(previousDataRef.current, data);

    if (!hasChanged) {
      // Data hasn't changed, ensure pending is false
      setIsPending(false);
      return;
    }

    // Set pending to true when data changes (before debounce delay)
    setIsPending(true);

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    // Set new timeout
    timeoutRef.current = setTimeout(() => {
      debouncedReview(data);
      previousDataRef.current = data;
    }, delay);

    // Cleanup function - handles both unmount and dependency changes
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [
    data,
    delay,
    enabled,
    skipInitialCall,
    debouncedReview,
    waypointsList,
    qgcMissionData,
    setWaypointsPreview,
    setWaypointsList,
  ]);

  // Reset pending state when component unmounts
  useEffect(() => {
    return () => {
      setIsPending(false);
    };
  }, []);

  return {
    debouncedReview,
    isPending, // Return pending state
  };
};
