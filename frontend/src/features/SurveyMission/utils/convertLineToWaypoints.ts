import { Waypoint } from '../types/surveyMission.types';

export const convertLineToWaypoints = (
  points: { lat: number; lng: number }[],
): Waypoint[] => {
  if (points.length < 2) {
    return [];
  }

  return points.map((point, index) => ({
    cruise_speed: 7,
    operating_altitude: 20,
    command: {
      value: 16, // MAV_CMD_NAV_WAYPOINT
      label: 'MAV_CMD_NAV_WAYPOINT',
    },
    frame: {
      value: 3, // MAV_FRAME_GLOBAL_RELATIVE_ALT
      label: 'MAV_FRAME_GLOBAL_RELATIVE_ALT',
    },
    param_1: 0, // Hold time in seconds
    param_2: 0, // Acceptance radius in meters
    param_3: 0, // Pass radius in meters
    param_4: 0, // Yaw angle in degrees
    latitude: point.lat,
    longitude: point.lng,
    altitude: 10, // Default altitude, can be adjusted
  }));
};

export const convertUnitValue = (data: string) => {
  const [value, unit] = String(data).split(' ');
  return { value: Number(value) || 0, unit: unit || '' };
};
